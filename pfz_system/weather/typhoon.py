"""
颱風/熱帶氣旋監測

整合多來源颱風資訊，提供：
- 活躍颱風追蹤
- 漁場影響評估
- 風險等級判定
- 作業建議

資料來源：
- JMA (日本氣象廳)
- JTWC (美國聯合颱風警報中心)
- CMA (中國氣象局)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import math

import requests
import numpy as np

logger = logging.getLogger(__name__)


class TyphoonCategory(Enum):
    """颱風強度分類 (日本氣象廳標準)"""
    TD = "TD"       # 熱帶性低氣壓 (<34 kt)
    TS = "TS"       # 熱帶風暴 (34-47 kt)
    STS = "STS"     # 強熱帶風暴 (48-63 kt)
    TY = "TY"       # 颱風 (64-84 kt)
    STY = "STY"     # 強烈颱風 (>84 kt)


class RiskLevel(Enum):
    """風險等級"""
    EXTREME = "extreme"     # 極端危險
    HIGH = "high"           # 高風險
    MODERATE = "moderate"   # 中等風險
    LOW = "low"             # 低風險
    NONE = "none"           # 無風險


@dataclass
class TyphoonPosition:
    """颱風位置資訊"""
    time: datetime
    lat: float
    lon: float
    max_wind_kt: float
    central_pressure_hpa: float
    movement_dir: float      # degrees (0 = N, 90 = E)
    movement_speed_kt: float


@dataclass
class TyphoonInfo:
    """
    颱風完整資訊
    
    Attributes:
        id: 颱風編號 (如 2401)
        name: 國際名稱
        name_local: 當地名稱
        category: 強度分類
        current: 當前位置資訊
        forecast_track: 預報路徑
        source: 數據來源
    """
    id: str
    name: str
    name_local: str
    category: TyphoonCategory
    current: TyphoonPosition
    forecast_track: List[TyphoonPosition] = field(default_factory=list)
    source: str = "JMA"
    
    @property
    def max_wind_ms(self) -> float:
        """最大風速 (m/s)"""
        return self.current.max_wind_kt * 0.514444
    
    @property
    def is_typhoon(self) -> bool:
        """是否達到颱風級別"""
        return self.category in [TyphoonCategory.TY, TyphoonCategory.STY]
    
    def get_info_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "name_local": self.name_local,
            "category": self.category.value,
            "lat": self.current.lat,
            "lon": self.current.lon,
            "max_wind_kt": self.current.max_wind_kt,
            "max_wind_ms": self.max_wind_ms,
            "central_pressure_hpa": self.current.central_pressure_hpa,
            "movement_dir": self.current.movement_dir,
            "movement_speed_kt": self.current.movement_speed_kt,
            "source": self.source
        }


@dataclass
class TyphoonImpact:
    """颱風影響評估結果"""
    typhoon: TyphoonInfo
    distance_nm: float            # 距離 (海里)
    distance_km: float            # 距離 (公里)
    hours_to_impact: Optional[float]  # 預計影響時間 (小時)
    risk_level: RiskLevel
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)


class TyphoonMonitor:
    """
    颱風監測器
    
    提供颱風追蹤、影響評估與作業建議。
    
    Example:
        >>> monitor = TyphoonMonitor()
        >>> typhoons = monitor.get_active_typhoons("WPAC")
        >>> for t in typhoons:
        ...     print(f"{t.name}: {t.category.value}")
        
        >>> impact = monitor.check_typhoon_impact(25.0, 140.0, radius_nm=300)
        >>> print(impact["recommendation"])
    """
    
    # 颱風警戒半徑 (海里)
    DEFAULT_RADIUS_NM = 300
    
    # 各等級的距離閾值
    RISK_THRESHOLDS = {
        RiskLevel.EXTREME: 100,   # nm
        RiskLevel.HIGH: 200,
        RiskLevel.MODERATE: 300,
        RiskLevel.LOW: 500
    }
    
    def __init__(self, timeout: int = 30):
        """
        初始化監測器
        
        Args:
            timeout: API 請求超時時間 (秒)
        """
        self.timeout = timeout
        self.session = requests.Session()
        self._cache: Dict[str, Any] = {}
    
    def _haversine(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> Tuple[float, float]:
        """
        計算兩點間距離
        
        Args:
            lat1, lon1: 第一點座標
            lat2, lon2: 第二點座標
            
        Returns:
            (距離_海里, 距離_公里)
        """
        R_nm = 3440.065  # 海里
        R_km = 6371.0    # 公里
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R_nm * c, R_km * c
    
    def _classify_category(self, max_wind_kt: float) -> TyphoonCategory:
        """
        根據風速判定颱風等級
        
        Args:
            max_wind_kt: 最大風速 (kt)
            
        Returns:
            颱風等級
        """
        if max_wind_kt >= 85:
            return TyphoonCategory.STY
        elif max_wind_kt >= 64:
            return TyphoonCategory.TY
        elif max_wind_kt >= 48:
            return TyphoonCategory.STS
        elif max_wind_kt >= 34:
            return TyphoonCategory.TS
        else:
            return TyphoonCategory.TD
    
    def _assess_risk_level(
        self,
        distance_nm: float,
        max_wind_kt: float
    ) -> RiskLevel:
        """
        評估風險等級
        
        Args:
            distance_nm: 距離 (海里)
            max_wind_kt: 颱風最大風速 (kt)
            
        Returns:
            風險等級
        """
        # 強颱風時增加風險權重
        wind_factor = 1.0
        if max_wind_kt >= 100:
            wind_factor = 1.5
        elif max_wind_kt >= 85:
            wind_factor = 1.3
        elif max_wind_kt >= 64:
            wind_factor = 1.1
        
        effective_distance = distance_nm / wind_factor
        
        if effective_distance < self.RISK_THRESHOLDS[RiskLevel.EXTREME]:
            return RiskLevel.EXTREME
        elif effective_distance < self.RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif effective_distance < self.RISK_THRESHOLDS[RiskLevel.MODERATE]:
            return RiskLevel.MODERATE
        elif effective_distance < self.RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        else:
            return RiskLevel.NONE
    
    def _get_recommendation(
        self,
        risk_level: RiskLevel,
        hours_to_impact: Optional[float]
    ) -> str:
        """
        生成作業建議
        
        Args:
            risk_level: 風險等級
            hours_to_impact: 預計影響時間
            
        Returns:
            建議文字
        """
        base_recommendations = {
            RiskLevel.EXTREME: "🚨 極端危險！立即停止作業，全速返港避風",
            RiskLevel.HIGH: "⛔ 高風險！建議 24 小時內返港避風",
            RiskLevel.MODERATE: "⚠️ 中等風險！密切關注颱風動態，做好撤離準備",
            RiskLevel.LOW: "📢 低風險！持續監測颱風路徑，正常作業",
            RiskLevel.NONE: "✅ 無颱風影響，可正常作業"
        }
        
        recommendation = base_recommendations.get(risk_level, "請謹慎評估")
        
        if hours_to_impact is not None and hours_to_impact < 48:
            recommendation += f"\n⏰ 預計 {hours_to_impact:.0f} 小時後可能受影響"
        
        return recommendation
    
    def get_active_typhoons(
        self,
        basin: str = "WPAC"
    ) -> List[TyphoonInfo]:
        """
        獲取當前活躍颱風
        
        Args:
            basin: 海域代碼
                - WPAC: 西太平洋
                - CPAC: 中太平洋
                - EPAC: 東太平洋
                - ATL: 大西洋
                - IO: 印度洋
                
        Returns:
            活躍颱風列表
            
        Note:
            目前返回模擬數據，實際部署時需接入真實 API
        """
        logger.info(f"Checking active typhoons in {basin}")
        
        # TODO: 實際部署時替換為真實 API 調用
        # 可用來源：
        # - JMA: https://www.jma.go.jp/bosai/typhoon/data/
        # - JTWC: https://www.metoc.navy.mil/jtwc/
        # - IBTrACS: https://www.ncei.noaa.gov/products/international-best-track-archive
        
        # 返回空列表（無活躍颱風時）
        return []
    
    def get_typhoon_by_id(self, typhoon_id: str) -> Optional[TyphoonInfo]:
        """
        根據編號獲取颱風資訊
        
        Args:
            typhoon_id: 颱風編號 (如 "2401")
            
        Returns:
            颱風資訊，不存在則返回 None
        """
        typhoons = self.get_active_typhoons()
        for typhoon in typhoons:
            if typhoon.id == typhoon_id:
                return typhoon
        return None
    
    def check_typhoon_impact(
        self,
        lat: float,
        lon: float,
        radius_nm: float = 300
    ) -> Dict[str, Any]:
        """
        檢查颱風對指定位置的影響
        
        Args:
            lat: 緯度
            lon: 經度
            radius_nm: 警戒半徑 (海里)
            
        Returns:
            影響評估報告
        """
        typhoons = self.get_active_typhoons()
        
        impacts: List[TyphoonImpact] = []
        
        for typhoon in typhoons:
            # 計算距離
            dist_nm, dist_km = self._haversine(
                lat, lon,
                typhoon.current.lat, typhoon.current.lon
            )
            
            if dist_nm > radius_nm * 1.5:
                continue  # 超出關注範圍
            
            # 計算預計影響時間
            hours_to_impact: Optional[float] = None
            if typhoon.current.movement_speed_kt > 0:
                hours_to_impact = dist_nm / typhoon.current.movement_speed_kt
            
            # 評估風險
            risk_level = self._assess_risk_level(dist_nm, typhoon.current.max_wind_kt)
            recommendation = self._get_recommendation(risk_level, hours_to_impact)
            
            impact = TyphoonImpact(
                typhoon=typhoon,
                distance_nm=round(dist_nm, 1),
                distance_km=round(dist_km, 1),
                hours_to_impact=round(hours_to_impact, 1) if hours_to_impact else None,
                risk_level=risk_level,
                recommendation=recommendation,
                details={
                    "bearing_from_typhoon": self._calculate_bearing(
                        typhoon.current.lat, typhoon.current.lon, lat, lon
                    )
                }
            )
            
            impacts.append(impact)
        
        # 按風險等級排序 (高風險在前)
        risk_order = {
            RiskLevel.EXTREME: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.LOW: 3,
            RiskLevel.NONE: 4
        }
        impacts.sort(key=lambda x: risk_order.get(x.risk_level, 99))
        
        # 生成總結
        if impacts:
            max_risk = impacts[0].risk_level
            overall_recommendation = self._get_recommendation(max_risk, None)
        else:
            max_risk = RiskLevel.NONE
            overall_recommendation = "✅ 無颱風影響，可正常作業"
        
        return {
            "location": {"lat": lat, "lon": lon},
            "check_time": datetime.utcnow().isoformat() + "Z",
            "has_impact": len(impacts) > 0,
            "max_risk_level": max_risk.value,
            "recommendation": overall_recommendation,
            "typhoon_count": len(impacts),
            "impacts": [
                {
                    "typhoon_id": imp.typhoon.id,
                    "typhoon_name": imp.typhoon.name,
                    "category": imp.typhoon.category.value,
                    "distance_nm": imp.distance_nm,
                    "distance_km": imp.distance_km,
                    "hours_to_impact": imp.hours_to_impact,
                    "risk_level": imp.risk_level.value,
                    "recommendation": imp.recommendation
                }
                for imp in impacts
            ]
        }
    
    def _calculate_bearing(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        計算從點1到點2的方位角
        
        Args:
            lat1, lon1: 起點座標
            lat2, lon2: 終點座標
            
        Returns:
            方位角 (0-360度，0=北)
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        
        x = math.sin(dlon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    def get_safety_assessment(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        獲取位置的安全評估報告
        
        Args:
            lat: 緯度
            lon: 經度
            
        Returns:
            安全評估報告
        """
        impact = self.check_typhoon_impact(lat, lon)
        
        # 建立安全等級
        risk_to_safety = {
            "none": "SAFE",
            "low": "CAUTION",
            "moderate": "WARNING",
            "high": "DANGER",
            "extreme": "EVACUATE"
        }
        
        safety_level = risk_to_safety.get(impact["max_risk_level"], "UNKNOWN")
        
        return {
            "location": impact["location"],
            "safety_level": safety_level,
            "typhoon_threat": impact["has_impact"],
            "details": impact,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


def check_route_safety(
    waypoints: List[Tuple[float, float]],
    departure_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    檢查航線安全性
    
    Args:
        waypoints: 航點列表 [(lat, lon), ...]
        departure_time: 出發時間
        
    Returns:
        航線安全評估
    """
    monitor = TyphoonMonitor()
    
    assessments = []
    max_risk = RiskLevel.NONE
    risk_order = {
        RiskLevel.EXTREME: 0,
        RiskLevel.HIGH: 1,
        RiskLevel.MODERATE: 2,
        RiskLevel.LOW: 3,
        RiskLevel.NONE: 4
    }
    
    for i, (lat, lon) in enumerate(waypoints):
        assessment = monitor.check_typhoon_impact(lat, lon)
        assessments.append({
            "waypoint": i,
            "lat": lat,
            "lon": lon,
            "risk_level": assessment["max_risk_level"],
            "recommendation": assessment["recommendation"]
        })
        
        current_risk = RiskLevel(assessment["max_risk_level"])
        if risk_order[current_risk] < risk_order[max_risk]:
            max_risk = current_risk
    
    return {
        "route_safe": max_risk in [RiskLevel.NONE, RiskLevel.LOW],
        "max_risk_level": max_risk.value,
        "waypoint_assessments": assessments,
        "recommendation": (
            "✅ 航線安全" if max_risk in [RiskLevel.NONE, RiskLevel.LOW]
            else f"⚠️ 航線存在風險 ({max_risk.value})"
        )
    }
