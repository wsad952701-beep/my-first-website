"""
潛在漁場區 (PFZ) 預測算法

整合多源數據計算漁場潛力分數，包括：
- 棲息地指數 (SST + Chl-a)
- 熱鋒面分數
- 渦旋分數
- 氣象適宜度
- 趨勢持續性

輸出：PFZ 分數 (0-100) 與作業建議
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

import numpy as np
import pandas as pd

try:
    from ..config import get_settings, get_species, Species
    from ..data.fetchers import BoundingBox, TimeRange, SSTFetcher, ChlaFetcher, SSHFetcher
    from ..weather import GlobalWeatherFetcher, OperabilityCalculator, VesselType, TyphoonMonitor
    from .fronts import FrontDetector, FrontDetectionResult
    from .eddies import EddyDetector, EddyDetectionResult
except ImportError:
    import sys
    import os
    # Add parent directory for cross-module imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    # Add current directory for local imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from config import get_settings, get_species, Species
    from data.fetchers import BoundingBox, TimeRange, SSTFetcher, ChlaFetcher, SSHFetcher
    from weather import GlobalWeatherFetcher, OperabilityCalculator, VesselType, TyphoonMonitor
    from fronts import FrontDetector, FrontDetectionResult
    from eddies import EddyDetector, EddyDetectionResult

logger = logging.getLogger(__name__)


@dataclass
class PFZScore:
    """
    PFZ 分數結果
    
    Attributes:
        total_score: 總分 (0-100)
        habitat_score: 棲息地指數
        front_score: 鋒面分數
        eddy_score: 渦旋分數
        weather_score: 氣象適宜度
        trend_score: 趨勢分數
        confidence: 信心度 (0-1)
        recommendation: 作業建議
    """
    total_score: float
    habitat_score: float
    front_score: float
    eddy_score: float
    weather_score: float
    trend_score: float
    confidence: float
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def level(self) -> str:
        """分數等級"""
        if self.total_score >= 80:
            return "極佳"
        elif self.total_score >= 60:
            return "良好"
        elif self.total_score >= 40:
            return "中等"
        elif self.total_score >= 20:
            return "較差"
        else:
            return "不佳"
    
    @property
    def color(self) -> str:
        """等級顏色 (hex)"""
        if self.total_score >= 80:
            return "#28a745"  # 綠
        elif self.total_score >= 60:
            return "#17a2b8"  # 青
        elif self.total_score >= 40:
            return "#ffc107"  # 黃
        elif self.total_score >= 20:
            return "#fd7e14"  # 橙
        else:
            return "#dc3545"  # 紅


@dataclass
class PFZPrediction:
    """
    PFZ 預測結果
    
    包含位置、時間與完整評估。
    """
    lat: float
    lon: float
    time: datetime
    score: PFZScore
    target_species: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "location": {"lat": self.lat, "lon": self.lon},
            "time": self.time.isoformat(),
            "total_score": self.score.total_score,
            "level": self.score.level,
            "color": self.score.color,
            "scores": {
                "habitat": self.score.habitat_score,
                "front": self.score.front_score,
                "eddy": self.score.eddy_score,
                "weather": self.score.weather_score,
                "trend": self.score.trend_score
            },
            "confidence": self.score.confidence,
            "recommendation": self.score.recommendation,
            "target_species": self.target_species,
            "metadata": self.metadata
        }


class PFZCalculator:
    """
    PFZ 計算器
    
    整合多源數據計算漁場潛力。
    
    Attributes:
        weights: 各因子權重
        species: 目標魚種
        vessel_type: 作業漁法
    
    Example:
        >>> calc = PFZCalculator(target_species="yellowfin_tuna")
        >>> prediction = calc.predict(lat=22.5, lon=121.0)
        >>> print(f"PFZ Score: {prediction.score.total_score}")
    """
    
    def __init__(
        self,
        target_species: Optional[str] = None,
        vessel_type: str = "longline",
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化 PFZ 計算器
        
        Args:
            target_species: 目標魚種 ID
            vessel_type: 漁法類型
            weights: 自定義權重
        """
        self.settings = get_settings()
        
        # 設定權重
        if weights:
            self.weights = weights
        else:
            self.weights = self.settings.algorithm.pfz_weights.copy()
        
        # 驗證權重
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            # 正規化
            self.weights = {k: v/total_weight for k, v in self.weights.items()}
        
        # 設定目標魚種
        self.species: Optional[Species] = None
        if target_species:
            self.species = get_species(target_species)
        
        # 設定漁法
        try:
            self.vessel_type = VesselType(vessel_type.lower())
        except ValueError:
            self.vessel_type = VesselType.GENERAL
        
        # 初始化數據獲取器
        self.sst_fetcher = SSTFetcher()
        self.chla_fetcher = ChlaFetcher()
        self.ssh_fetcher = SSHFetcher()
        self.weather_fetcher = GlobalWeatherFetcher()
        
        # 初始化算法
        self.front_detector = FrontDetector()
        self.eddy_detector = EddyDetector()
        self.operability_calculator = OperabilityCalculator(self.vessel_type)
        self.typhoon_monitor = TyphoonMonitor()
    
    def predict(
        self,
        lat: float,
        lon: float,
        forecast_days: int = 3
    ) -> PFZPrediction:
        """
        計算單點 PFZ 預測
        
        Args:
            lat: 緯度
            lon: 經度
            forecast_days: 預報天數
            
        Returns:
            PFZPrediction
        """
        logger.info(f"Calculating PFZ for ({lat}, {lon})")
        
        scores = {}
        confidence_factors = []
        details = {}
        
        # 1. 棲息地指數 (SST + Chl-a)
        try:
            sst = self._get_sst(lat, lon)
            chla = self._get_chla(lat, lon)
            
            if self.species:
                habitat_score = self.species.get_habitat_score(sst, chla)
            else:
                # 通用評估
                habitat_score = self._calculate_generic_habitat(sst, chla)
            
            scores["habitat"] = habitat_score
            confidence_factors.append(0.9 if sst else 0.5)
            details["sst"] = sst
            details["chla"] = chla
            
        except Exception as e:
            logger.warning(f"Habitat calculation failed: {e}")
            scores["habitat"] = 50.0
            confidence_factors.append(0.3)
        
        # 2. 鋒面分數
        try:
            front_result = self._detect_fronts(lat, lon)
            front_score = self.front_detector.get_front_score(
                lat, lon, front_result.fronts
            )
            scores["front"] = front_score
            confidence_factors.append(0.8)
            details["front_count"] = front_result.front_count
            
        except Exception as e:
            logger.warning(f"Front detection failed: {e}")
            scores["front"] = 0.0
            confidence_factors.append(0.3)
        
        # 3. 渦旋分數
        try:
            eddy_result = self._detect_eddies(lat, lon)
            eddy_score = self.eddy_detector.get_eddy_score(
                lat, lon, eddy_result.eddies,
                fishing_preference="edge"
            )
            scores["eddy"] = eddy_score
            confidence_factors.append(0.8)
            details["eddy_count"] = len(eddy_result.eddies)
            
        except Exception as e:
            logger.warning(f"Eddy detection failed: {e}")
            scores["eddy"] = 0.0
            confidence_factors.append(0.3)
        
        # 4. 氣象適宜度
        try:
            weather = self._get_weather(lat, lon, forecast_days)
            
            if not weather.empty:
                wind = weather.get("wind_speed_10m_mean", pd.Series([10])).iloc[0]
                wave = weather.get("wave_height", pd.Series([1.5])).iloc[0]
                vis = weather.get("visibility_mean", pd.Series([10000])).iloc[0]
                precip = weather.get("precipitation_mean", pd.Series([0])).iloc[0]
                
                op_result = self.operability_calculator.calculate(
                    wind_speed=wind if pd.notna(wind) else 10,
                    wave_height=wave if pd.notna(wave) else None,
                    visibility=vis if pd.notna(vis) else None,
                    precipitation=precip if pd.notna(precip) else None
                )
                
                scores["weather"] = op_result.score
                confidence_factors.append(0.9)
                details["operability"] = op_result.level.value
            else:
                scores["weather"] = 70.0
                confidence_factors.append(0.5)
                
        except Exception as e:
            logger.warning(f"Weather calculation failed: {e}")
            scores["weather"] = 70.0
            confidence_factors.append(0.4)
        
        # 5. 趨勢分數 (簡化版，基於當前數據的穩定性)
        scores["trend"] = 60.0  # 默認中等
        confidence_factors.append(0.6)
        
        # 6. 颱風風險檢查
        try:
            typhoon_impact = self.typhoon_monitor.check_typhoon_impact(lat, lon)
            if typhoon_impact["has_impact"]:
                # 降低分數
                risk_penalty = {
                    "none": 0,
                    "low": 10,
                    "moderate": 30,
                    "high": 60,
                    "extreme": 100
                }
                penalty = risk_penalty.get(typhoon_impact["max_risk_level"], 0)
                scores["weather"] = max(0, scores["weather"] - penalty)
                details["typhoon_risk"] = typhoon_impact["max_risk_level"]
        except Exception as e:
            logger.debug(f"Typhoon check failed: {e}")
        
        # 計算總分
        total_score = sum(
            scores.get(key, 0) * weight
            for key, weight in self.weights.items()
            if key in scores
        )
        
        # 計算信心度
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
        
        # 生成建議
        recommendation = self._generate_recommendation(
            total_score, scores, details
        )
        
        # 構建結果
        pfz_score = PFZScore(
            total_score=round(total_score, 1),
            habitat_score=round(scores.get("habitat", 0), 1),
            front_score=round(scores.get("front", 0), 1),
            eddy_score=round(scores.get("eddy", 0), 1),
            weather_score=round(scores.get("weather", 0), 1),
            trend_score=round(scores.get("trend", 0), 1),
            confidence=round(confidence, 2),
            recommendation=recommendation,
            details=details
        )
        
        return PFZPrediction(
            lat=lat,
            lon=lon,
            time=datetime.utcnow(),
            score=pfz_score,
            target_species=self.species.id if self.species else None,
            metadata={
                "weights": self.weights,
                "vessel_type": self.vessel_type.value
            }
        )
    
    def predict_grid(
        self,
        bbox: BoundingBox,
        resolution: float = 0.5,
        forecast_days: int = 3
    ) -> pd.DataFrame:
        """
        計算區域網格 PFZ 預測
        
        Args:
            bbox: 區域邊界
            resolution: 網格分辨率 (度)
            forecast_days: 預報天數
            
        Returns:
            包含各點 PFZ 分數的 DataFrame
        """
        lats = np.arange(bbox.lat_min, bbox.lat_max + resolution, resolution)
        lons = np.arange(bbox.lon_min, bbox.lon_max + resolution, resolution)
        
        results = []
        
        for lat in lats:
            for lon in lons:
                try:
                    pred = self.predict(lat, lon, forecast_days)
                    results.append({
                        "lat": lat,
                        "lon": lon,
                        "pfz_score": pred.score.total_score,
                        "level": pred.score.level,
                        "color": pred.score.color,
                        "habitat": pred.score.habitat_score,
                        "front": pred.score.front_score,
                        "eddy": pred.score.eddy_score,
                        "weather": pred.score.weather_score,
                        "confidence": pred.score.confidence
                    })
                except Exception as e:
                    logger.warning(f"Grid point ({lat}, {lon}) failed: {e}")
                    results.append({
                        "lat": lat,
                        "lon": lon,
                        "pfz_score": 0,
                        "level": "N/A",
                        "color": "#999999"
                    })
        
        return pd.DataFrame(results)
    
    def _get_sst(self, lat: float, lon: float) -> Optional[float]:
        """獲取 SST"""
        return self.sst_fetcher.get_latest_sst(lat, lon)
    
    def _get_chla(self, lat: float, lon: float) -> Optional[float]:
        """獲取 Chl-a"""
        bbox = BoundingBox(lat - 0.5, lat + 0.5, lon - 0.5, lon + 0.5)
        result = self.chla_fetcher.fetch(bbox)
        
        if result.data is not None and not result.data.empty:
            return result.data["chla"].mean()
        return None
    
    def _detect_fronts(
        self,
        lat: float,
        lon: float,
        radius: float = 2.0
    ) -> FrontDetectionResult:
        """檢測周邊鋒面"""
        bbox = BoundingBox(lat - radius, lat + radius, lon - radius, lon + radius)
        sst_result = self.sst_fetcher.fetch(bbox)
        
        if sst_result.data is not None and not sst_result.data.empty:
            return self.front_detector.detect_from_dataframe(sst_result.data)
        
        return FrontDetectionResult(fronts=[], gradient_field=np.array([]))
    
    def _detect_eddies(
        self,
        lat: float,
        lon: float,
        radius: float = 3.0
    ) -> EddyDetectionResult:
        """檢測周邊渦旋"""
        bbox = BoundingBox(lat - radius, lat + radius, lon - radius, lon + radius)
        ssh_result = self.ssh_fetcher.fetch(bbox)
        
        if ssh_result.data is not None and not ssh_result.data.empty:
            return self.eddy_detector.detect_from_dataframe(ssh_result.data)
        
        return EddyDetectionResult(eddies=[], sla_field=np.array([]))
    
    def _get_weather(
        self,
        lat: float,
        lon: float,
        forecast_days: int
    ) -> pd.DataFrame:
        """獲取氣象預報"""
        return self.weather_fetcher.fetch_ensemble(
            lat, lon,
            forecast_days=forecast_days,
            include_marine=True
        )
    
    def _calculate_generic_habitat(
        self,
        sst: Optional[float],
        chla: Optional[float]
    ) -> float:
        """通用棲息地評估"""
        score = 50.0
        
        if sst is not None:
            # 最佳範圍 24-28°C
            if 24 <= sst <= 28:
                sst_score = 100
            elif 20 <= sst < 24:
                sst_score = 50 + (sst - 20) * 12.5
            elif 28 < sst <= 32:
                sst_score = 100 - (sst - 28) * 12.5
            else:
                sst_score = max(0, 50 - abs(sst - 26) * 5)
            
            score = sst_score * 0.7
        
        if chla is not None:
            # 最佳範圍 0.2-1.0 mg/m³
            if 0.2 <= chla <= 1.0:
                chla_score = 100
            elif chla < 0.2:
                chla_score = chla / 0.2 * 80
            else:
                chla_score = max(0, 100 - (chla - 1.0) * 20)
            
            score += chla_score * 0.3
        
        return score
    
    def _generate_recommendation(
        self,
        total_score: float,
        scores: Dict[str, float],
        details: Dict[str, Any]
    ) -> str:
        """生成作業建議"""
        if total_score >= 80:
            base = "🎯 極佳漁場！建議優先作業。"
        elif total_score >= 60:
            base = "✅ 良好條件，適合作業。"
        elif total_score >= 40:
            base = "⚠️ 中等條件，可嘗試作業。"
        elif total_score >= 20:
            base = "⚡ 條件較差，建議觀望或轉場。"
        else:
            base = "❌ 不建議作業，考慮其他漁場。"
        
        # 添加具體建議
        tips = []
        
        if scores.get("front", 0) >= 50:
            tips.append("附近有鋒面，餌料魚可能聚集")
        
        if scores.get("eddy", 0) >= 50:
            tips.append("渦旋區域，注意流向")
        
        if scores.get("weather", 0) < 50:
            operability = details.get("operability", "")
            tips.append(f"氣象條件一般 ({operability})")
        
        if details.get("typhoon_risk"):
            tips.append(f"⚠️ 颱風風險：{details['typhoon_risk']}")
        
        if tips:
            return base + " " + "、".join(tips) + "。"
        
        return base


def calculate_pfz(
    lat: float,
    lon: float,
    target_species: Optional[str] = None
) -> PFZPrediction:
    """
    便捷函數：計算 PFZ
    
    Args:
        lat: 緯度
        lon: 經度
        target_species: 目標魚種
        
    Returns:
        PFZPrediction
    """
    calc = PFZCalculator(target_species=target_species)
    return calc.predict(lat, lon)
