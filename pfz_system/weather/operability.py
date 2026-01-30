"""
漁業作業適宜度評估

根據氣象條件評估不同漁法的作業適宜度，包括：
- 風速影響
- 波高影響
- 能見度影響
- 降水影響
- 綜合評分

支持的漁法：
- 圍網 (purse_seine)
- 延繩釣 (longline)
- 竿釣 (pole_and_line)
- 刺網 (gillnet)
- 拖網 (trawl)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

import pandas as pd
import numpy as np

from .global_models import GlobalWeatherFetcher, get_weather_forecast

logger = logging.getLogger(__name__)


class VesselType(Enum):
    """船舶/漁法類型"""
    PURSE_SEINE = "purse_seine"       # 圍網
    LONGLINE = "longline"              # 延繩釣
    POLE_AND_LINE = "pole_and_line"    # 竿釣
    GILLNET = "gillnet"                # 刺網
    TRAWL = "trawl"                    # 拖網
    SQUID_JIGGING = "squid_jigging"    # 魷釣
    GENERAL = "general"                # 一般


class OperabilityLevel(Enum):
    """作業適宜度等級"""
    EXCELLENT = "excellent"     # 極佳 (90-100)
    GOOD = "good"               # 良好 (70-89)
    MODERATE = "moderate"       # 中等 (50-69)
    MARGINAL = "marginal"       # 勉強 (30-49)
    POOR = "poor"               # 不佳 (10-29)
    DANGEROUS = "dangerous"     # 危險 (0-9)


@dataclass
class OperabilityThresholds:
    """
    各漁法的作業閾值
    
    Attributes:
        wind_optimal: 最佳風速上限 (m/s)
        wind_max: 最大可作業風速 (m/s)
        wave_optimal: 最佳波高上限 (m)
        wave_max: 最大可作業波高 (m)
        visibility_min: 最低能見度 (m)
        precipitation_max: 最大降水量 (mm/h)
    """
    vessel_type: VesselType
    wind_optimal: float  # m/s
    wind_max: float      # m/s
    wave_optimal: float  # m
    wave_max: float      # m
    visibility_min: float  # m
    precipitation_max: float  # mm/h


# 各漁法閾值配置
VESSEL_THRESHOLDS: Dict[VesselType, OperabilityThresholds] = {
    VesselType.PURSE_SEINE: OperabilityThresholds(
        vessel_type=VesselType.PURSE_SEINE,
        wind_optimal=7.0,
        wind_max=12.0,
        wave_optimal=1.5,
        wave_max=2.5,
        visibility_min=3000,
        precipitation_max=5.0
    ),
    VesselType.LONGLINE: OperabilityThresholds(
        vessel_type=VesselType.LONGLINE,
        wind_optimal=10.0,
        wind_max=15.0,
        wave_optimal=2.0,
        wave_max=3.5,
        visibility_min=2000,
        precipitation_max=10.0
    ),
    VesselType.POLE_AND_LINE: OperabilityThresholds(
        vessel_type=VesselType.POLE_AND_LINE,
        wind_optimal=5.0,
        wind_max=10.0,
        wave_optimal=1.0,
        wave_max=2.0,
        visibility_min=5000,
        precipitation_max=3.0
    ),
    VesselType.GILLNET: OperabilityThresholds(
        vessel_type=VesselType.GILLNET,
        wind_optimal=8.0,
        wind_max=13.0,
        wave_optimal=1.5,
        wave_max=3.0,
        visibility_min=2000,
        precipitation_max=8.0
    ),
    VesselType.TRAWL: OperabilityThresholds(
        vessel_type=VesselType.TRAWL,
        wind_optimal=12.0,
        wind_max=18.0,
        wave_optimal=2.5,
        wave_max=4.0,
        visibility_min=1000,
        precipitation_max=15.0
    ),
    VesselType.SQUID_JIGGING: OperabilityThresholds(
        vessel_type=VesselType.SQUID_JIGGING,
        wind_optimal=6.0,
        wind_max=11.0,
        wave_optimal=1.2,
        wave_max=2.2,
        visibility_min=3000,
        precipitation_max=5.0
    ),
    VesselType.GENERAL: OperabilityThresholds(
        vessel_type=VesselType.GENERAL,
        wind_optimal=10.0,
        wind_max=15.0,
        wave_optimal=2.0,
        wave_max=3.0,
        visibility_min=2000,
        precipitation_max=10.0
    ),
}


@dataclass
class OperabilityResult:
    """作業適宜度評估結果"""
    score: float                    # 0-100 分
    level: OperabilityLevel         # 等級
    wind_score: float               # 風速分項 (0-100)
    wave_score: float               # 波高分項 (0-100)
    visibility_score: float         # 能見度分項 (0-100)
    precipitation_score: float      # 降水分項 (0-100)
    limiting_factor: str            # 限制因素
    recommendation: str             # 作業建議
    details: Dict[str, Any] = field(default_factory=dict)


class OperabilityCalculator:
    """
    漁業作業適宜度計算器
    
    根據氣象條件計算各漁法的作業適宜度分數，
    並提供作業建議。
    
    Example:
        >>> calc = OperabilityCalculator(VesselType.LONGLINE)
        >>> result = calc.calculate(
        ...     wind_speed=8.0,
        ...     wave_height=1.5,
        ...     visibility=5000,
        ...     precipitation=0.0
        ... )
        >>> print(f"Score: {result.score}, Level: {result.level.value}")
    """
    
    # 分項權重
    WEIGHTS = {
        "wind": 0.40,
        "wave": 0.35,
        "visibility": 0.15,
        "precipitation": 0.10
    }
    
    def __init__(self, vessel_type: VesselType = VesselType.GENERAL):
        """
        初始化計算器
        
        Args:
            vessel_type: 船舶/漁法類型
        """
        self.vessel_type = vessel_type
        self.thresholds = VESSEL_THRESHOLDS.get(
            vessel_type,
            VESSEL_THRESHOLDS[VesselType.GENERAL]
        )
    
    def _calculate_wind_score(self, wind_speed: float) -> float:
        """
        計算風速分數
        
        Args:
            wind_speed: 風速 (m/s)
            
        Returns:
            0-100 分數
        """
        if wind_speed <= self.thresholds.wind_optimal:
            return 100.0
        elif wind_speed >= self.thresholds.wind_max:
            return 0.0
        else:
            # 線性遞減
            range_val = self.thresholds.wind_max - self.thresholds.wind_optimal
            excess = wind_speed - self.thresholds.wind_optimal
            return max(0, 100 * (1 - excess / range_val))
    
    def _calculate_wave_score(self, wave_height: float) -> float:
        """
        計算波高分數
        
        Args:
            wave_height: 波高 (m)
            
        Returns:
            0-100 分數
        """
        if wave_height <= self.thresholds.wave_optimal:
            return 100.0
        elif wave_height >= self.thresholds.wave_max:
            return 0.0
        else:
            range_val = self.thresholds.wave_max - self.thresholds.wave_optimal
            excess = wave_height - self.thresholds.wave_optimal
            return max(0, 100 * (1 - excess / range_val))
    
    def _calculate_visibility_score(self, visibility: float) -> float:
        """
        計算能見度分數
        
        Args:
            visibility: 能見度 (m)
            
        Returns:
            0-100 分數
        """
        excellent_vis = 10000  # 10km 以上為滿分
        min_vis = self.thresholds.visibility_min
        
        if visibility >= excellent_vis:
            return 100.0
        elif visibility <= min_vis:
            return 0.0
        else:
            # 對數遞減更符合人眼感知
            return 100 * np.log(visibility / min_vis) / np.log(excellent_vis / min_vis)
    
    def _calculate_precipitation_score(self, precipitation: float) -> float:
        """
        計算降水分數
        
        Args:
            precipitation: 降水量 (mm/h)
            
        Returns:
            0-100 分數
        """
        if precipitation <= 0:
            return 100.0
        elif precipitation >= self.thresholds.precipitation_max:
            return 0.0
        else:
            return max(0, 100 * (1 - precipitation / self.thresholds.precipitation_max))
    
    def _get_limiting_factor(
        self,
        scores: Dict[str, float]
    ) -> str:
        """
        找出主要限制因素
        
        Args:
            scores: 各分項分數
            
        Returns:
            限制因素名稱
        """
        factor_names = {
            "wind": "風速過大",
            "wave": "波高過高",
            "visibility": "能見度不足",
            "precipitation": "降水過多"
        }
        
        min_factor = min(scores, key=lambda k: scores[k])
        return factor_names.get(min_factor, "綜合條件")
    
    def _get_level(self, score: float) -> OperabilityLevel:
        """
        根據分數判定等級
        
        Args:
            score: 綜合分數 (0-100)
            
        Returns:
            適宜度等級
        """
        if score >= 90:
            return OperabilityLevel.EXCELLENT
        elif score >= 70:
            return OperabilityLevel.GOOD
        elif score >= 50:
            return OperabilityLevel.MODERATE
        elif score >= 30:
            return OperabilityLevel.MARGINAL
        elif score >= 10:
            return OperabilityLevel.POOR
        else:
            return OperabilityLevel.DANGEROUS
    
    def _get_recommendation(
        self,
        level: OperabilityLevel,
        limiting_factor: str
    ) -> str:
        """
        生成作業建議
        
        Args:
            level: 適宜度等級
            limiting_factor: 限制因素
            
        Returns:
            建議文字
        """
        recommendations = {
            OperabilityLevel.EXCELLENT: "☀️ 最佳作業條件，建議把握時機",
            OperabilityLevel.GOOD: "✅ 良好條件，可正常作業",
            OperabilityLevel.MODERATE: f"⚠️ 中等條件（{limiting_factor}），注意安全",
            OperabilityLevel.MARGINAL: f"⚠️ 勉強可作業（{limiting_factor}），需評估風險",
            OperabilityLevel.POOR: f"❌ 不建議作業（{limiting_factor}），考慮返港",
            OperabilityLevel.DANGEROUS: "🚨 危險！立即停止作業，返港避險"
        }
        return recommendations.get(level, "請謹慎評估")
    
    def calculate(
        self,
        wind_speed: float,
        wave_height: Optional[float] = None,
        visibility: Optional[float] = None,
        precipitation: Optional[float] = None
    ) -> OperabilityResult:
        """
        計算作業適宜度
        
        Args:
            wind_speed: 風速 (m/s)
            wave_height: 波高 (m)，可選
            visibility: 能見度 (m)，可選
            precipitation: 降水量 (mm/h)，可選
            
        Returns:
            適宜度評估結果
        """
        # 計算各分項分數
        wind_score = self._calculate_wind_score(wind_speed)
        
        wave_score = (
            self._calculate_wave_score(wave_height)
            if wave_height is not None else 80.0
        )
        
        vis_score = (
            self._calculate_visibility_score(visibility)
            if visibility is not None else 80.0
        )
        
        precip_score = (
            self._calculate_precipitation_score(precipitation)
            if precipitation is not None else 100.0
        )
        
        scores = {
            "wind": wind_score,
            "wave": wave_score,
            "visibility": vis_score,
            "precipitation": precip_score
        }
        
        # 加權計算總分
        total_score = sum(
            scores[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )
        
        # 判定等級和建議
        limiting_factor = self._get_limiting_factor(scores)
        level = self._get_level(total_score)
        recommendation = self._get_recommendation(level, limiting_factor)
        
        return OperabilityResult(
            score=round(total_score, 1),
            level=level,
            wind_score=round(wind_score, 1),
            wave_score=round(wave_score, 1),
            visibility_score=round(vis_score, 1),
            precipitation_score=round(precip_score, 1),
            limiting_factor=limiting_factor,
            recommendation=recommendation,
            details={
                "vessel_type": self.vessel_type.value,
                "thresholds": {
                    "wind_max": self.thresholds.wind_max,
                    "wave_max": self.thresholds.wave_max,
                    "visibility_min": self.thresholds.visibility_min
                },
                "input": {
                    "wind_speed": wind_speed,
                    "wave_height": wave_height,
                    "visibility": visibility,
                    "precipitation": precipitation
                }
            }
        )
    
    def calculate_from_dataframe(
        self,
        df: pd.DataFrame,
        wind_col: str = "wind_speed_10m_mean",
        wave_col: str = "wave_height",
        vis_col: str = "visibility_mean",
        precip_col: str = "precipitation_mean"
    ) -> pd.DataFrame:
        """
        從 DataFrame 批量計算適宜度
        
        Args:
            df: 氣象數據 DataFrame
            wind_col: 風速列名
            wave_col: 波高列名
            vis_col: 能見度列名
            precip_col: 降水列名
            
        Returns:
            添加適宜度欄位的 DataFrame
        """
        results = []
        
        for idx, row in df.iterrows():
            wind = row.get(wind_col, 0)
            wave = row.get(wave_col) if wave_col in df.columns else None
            vis = row.get(vis_col) if vis_col in df.columns else None
            precip = row.get(precip_col) if precip_col in df.columns else None
            
            result = self.calculate(
                wind_speed=wind if pd.notna(wind) else 0,
                wave_height=wave if pd.notna(wave) else None,
                visibility=vis if pd.notna(vis) else None,
                precipitation=precip if pd.notna(precip) else None
            )
            
            results.append({
                "operability_score": result.score,
                "operability_level": result.level.value,
                "limiting_factor": result.limiting_factor,
                "recommendation": result.recommendation
            })
        
        result_df = pd.DataFrame(results)
        return pd.concat([df.reset_index(drop=True), result_df], axis=1)


def get_operability_forecast(
    lat: float,
    lon: float,
    vessel_type: str = "general",
    forecast_days: int = 3
) -> pd.DataFrame:
    """
    便捷函數：獲取作業適宜度預報
    
    Args:
        lat: 緯度
        lon: 經度
        vessel_type: 漁法類型
        forecast_days: 預報天數
        
    Returns:
        包含適宜度預報的 DataFrame
        
    Example:
        >>> df = get_operability_forecast(25.0, 121.5, "longline", 3)
        >>> print(df[['time', 'operability_score', 'recommendation']].head())
    """
    # 獲取氣象預報
    weather = get_weather_forecast(lat, lon, forecast_days, include_marine=True)
    
    if weather.empty:
        logger.error(f"No weather data for ({lat}, {lon})")
        return pd.DataFrame()
    
    # 解析漁法類型
    try:
        vtype = VesselType(vessel_type.lower())
    except ValueError:
        logger.warning(f"Unknown vessel type '{vessel_type}', using 'general'")
        vtype = VesselType.GENERAL
    
    # 計算適宜度
    calculator = OperabilityCalculator(vtype)
    return calculator.calculate_from_dataframe(weather)


def get_best_operation_windows(
    lat: float,
    lon: float,
    vessel_type: str = "general",
    forecast_days: int = 3,
    min_score: float = 70.0,
    min_duration_hours: int = 6
) -> List[Dict[str, Any]]:
    """
    找出最佳作業時段
    
    Args:
        lat: 緯度
        lon: 經度
        vessel_type: 漁法類型
        forecast_days: 預報天數
        min_score: 最低分數閾值
        min_duration_hours: 最短持續時間 (小時)
        
    Returns:
        最佳作業時段列表
    """
    df = get_operability_forecast(lat, lon, vessel_type, forecast_days)
    
    if df.empty or "operability_score" not in df.columns:
        return []
    
    # 標記達標時段
    df["is_good"] = df["operability_score"] >= min_score
    
    # 找出連續的好時段
    windows = []
    current_window_start = None
    
    for idx, row in df.iterrows():
        if row["is_good"]:
            if current_window_start is None:
                current_window_start = row["time"]
        else:
            if current_window_start is not None:
                window_end = df.loc[idx - 1, "time"] if idx > 0 else current_window_start
                duration = (window_end - current_window_start).total_seconds() / 3600
                
                if duration >= min_duration_hours:
                    window_df = df[
                        (df["time"] >= current_window_start) &
                        (df["time"] <= window_end)
                    ]
                    
                    windows.append({
                        "start": current_window_start.isoformat(),
                        "end": window_end.isoformat(),
                        "duration_hours": duration,
                        "avg_score": window_df["operability_score"].mean(),
                        "min_score": window_df["operability_score"].min()
                    })
                
                current_window_start = None
    
    # 處理最後一個時段
    if current_window_start is not None:
        window_end = df.iloc[-1]["time"]
        duration = (window_end - current_window_start).total_seconds() / 3600
        
        if duration >= min_duration_hours:
            window_df = df[df["time"] >= current_window_start]
            windows.append({
                "start": current_window_start.isoformat(),
                "end": window_end.isoformat(),
                "duration_hours": duration,
                "avg_score": window_df["operability_score"].mean(),
                "min_score": window_df["operability_score"].min()
            })
    
    # 按平均分數排序
    return sorted(windows, key=lambda w: w["avg_score"], reverse=True)
