"""
中尺度渦旋檢測算法

基於 SSH 數據識別海洋中尺度渦旋：
- 氣旋渦旋 (Cyclonic) - 冷心，上升流
- 反氣旋渦旋 (Anticyclonic) - 暖心，下沉流

渦旋對漁業的影響：
- 冷心渦旋：營養鹽上湧，初級生產力高
- 暖心渦旋：溫暖穩定，大型魚聚集
- 渦旋邊緣：鋒面效應，餌料豐富
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import logging

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.interpolate import griddata

logger = logging.getLogger(__name__)


class EddyType(Enum):
    """渦旋類型"""
    CYCLONIC = "cyclonic"           # 氣旋（冷心）
    ANTICYCLONIC = "anticyclonic"   # 反氣旋（暖心）


@dataclass
class Eddy:
    """
    渦旋對象
    
    Attributes:
        eddy_type: 渦旋類型
        center_lat: 中心緯度
        center_lon: 中心經度
        radius_km: 半徑 (km)
        ssh_anomaly: SSH 異常值 (m)
        intensity: 強度指數 (0-100)
        rotation: 旋轉方向 (CW/CCW)
    """
    eddy_type: EddyType
    center_lat: float
    center_lon: float
    radius_km: float
    ssh_anomaly: float      # 正值=反氣旋，負值=氣旋
    intensity: float        # 0-100
    rotation: str = ""      # CW (順時針) 或 CCW (逆時針)
    
    def __post_init__(self):
        """設定旋轉方向"""
        if not self.rotation:
            # 北半球：氣旋=CCW，反氣旋=CW
            if self.center_lat >= 0:
                self.rotation = "CCW" if self.eddy_type == EddyType.CYCLONIC else "CW"
            else:
                self.rotation = "CW" if self.eddy_type == EddyType.CYCLONIC else "CCW"
    
    @property
    def is_cyclonic(self) -> bool:
        """是否為氣旋渦旋"""
        return self.eddy_type == EddyType.CYCLONIC
    
    @property
    def description(self) -> str:
        """描述"""
        if self.is_cyclonic:
            return "冷心渦旋，上升流區域，營養鹽豐富"
        else:
            return "暖心渦旋，穩定水團，大型魚類聚集"
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "type": self.eddy_type.value,
            "center": {"lat": self.center_lat, "lon": self.center_lon},
            "radius_km": self.radius_km,
            "ssh_anomaly_m": self.ssh_anomaly,
            "intensity": self.intensity,
            "rotation": self.rotation,
            "description": self.description
        }


@dataclass
class EddyDetectionResult:
    """渦旋檢測結果"""
    eddies: List[Eddy]
    sla_field: np.ndarray
    detection_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def cyclonic_count(self) -> int:
        """氣旋渦旋數量"""
        return sum(1 for e in self.eddies if e.is_cyclonic)
    
    @property
    def anticyclonic_count(self) -> int:
        """反氣旋渦旋數量"""
        return sum(1 for e in self.eddies if not e.is_cyclonic)


class EddyDetector:
    """
    中尺度渦旋檢測器
    
    基於 SSH 異常識別渦旋結構。
    
    Attributes:
        ssh_threshold: SLA 閾值 (m)
        min_radius_km: 最小渦旋半徑 (km)
        max_radius_km: 最大渦旋半徑 (km)
    
    Example:
        >>> detector = EddyDetector()
        >>> ssh_data = pd.DataFrame({'lat': [...], 'lon': [...], 'ssh': [...]})
        >>> result = detector.detect_from_dataframe(ssh_data)
        >>> for eddy in result.eddies:
        ...     print(f"{eddy.eddy_type.value}: ({eddy.center_lat}, {eddy.center_lon})")
    """
    
    def __init__(
        self,
        ssh_threshold: float = 0.05,
        min_radius_km: float = 50.0,
        max_radius_km: float = 300.0,
        resolution_km: float = 10.0
    ):
        """
        初始化渦旋檢測器
        
        Args:
            ssh_threshold: SLA 閾值 (m)，超過此值視為渦旋
            min_radius_km: 最小渦旋半徑 (km)
            max_radius_km: 最大渦旋半徑 (km)
            resolution_km: 數據分辨率 (km)
        """
        self.ssh_threshold = ssh_threshold
        self.min_radius_km = min_radius_km
        self.max_radius_km = max_radius_km
        self.resolution_km = resolution_km
    
    def detect_from_dataframe(
        self,
        ssh_data: pd.DataFrame,
        lat_col: str = "lat",
        lon_col: str = "lon",
        ssh_col: str = "ssh"
    ) -> EddyDetectionResult:
        """
        從 DataFrame 檢測渦旋
        
        Args:
            ssh_data: SSH 數據 DataFrame
            lat_col, lon_col, ssh_col: 列名
            
        Returns:
            EddyDetectionResult
        """
        if ssh_data.empty:
            return EddyDetectionResult(eddies=[], sla_field=np.array([]))
        
        df = ssh_data.copy()
        
        # 計算 SLA
        mean_ssh = df[ssh_col].mean()
        df["sla"] = df[ssh_col] - mean_ssh
        
        # 創建規則網格
        lats = np.sort(df[lat_col].unique())
        lons = np.sort(df[lon_col].unique())
        
        grid_lat, grid_lon = np.meshgrid(lats, lons, indexing='ij')
        
        points = df[[lat_col, lon_col]].values
        values = df["sla"].values
        
        sla_grid = griddata(points, values, (grid_lat, grid_lon), method='linear')
        sla_grid = np.nan_to_num(sla_grid, nan=0)
        
        lat_range = (lats.min(), lats.max())
        lon_range = (lons.min(), lons.max())
        
        return self.detect_from_grid(sla_grid, lat_range, lon_range)
    
    def detect_from_grid(
        self,
        sla_grid: np.ndarray,
        lat_range: Tuple[float, float],
        lon_range: Tuple[float, float]
    ) -> EddyDetectionResult:
        """
        從 SLA 網格檢測渦旋
        
        Args:
            sla_grid: 2D SLA 網格
            lat_range: 緯度範圍
            lon_range: 經度範圍
            
        Returns:
            EddyDetectionResult
        """
        eddies = []
        nrows, ncols = sla_grid.shape
        
        if nrows == 0 or ncols == 0:
            return EddyDetectionResult(eddies=[], sla_field=sla_grid)
        
        lat_step = (lat_range[1] - lat_range[0]) / max(1, nrows - 1)
        lon_step = (lon_range[1] - lon_range[0]) / max(1, ncols - 1)
        
        # 檢測反氣旋渦旋 (正 SLA)
        anticyclonic_mask = sla_grid > self.ssh_threshold
        labeled_ac, num_ac = ndimage.label(anticyclonic_mask)
        
        for label_id in range(1, num_ac + 1):
            eddy = self._extract_eddy(
                sla_grid, labeled_ac == label_id,
                lat_range, lon_range, lat_step, lon_step,
                EddyType.ANTICYCLONIC
            )
            if eddy:
                eddies.append(eddy)
        
        # 檢測氣旋渦旋 (負 SLA)
        cyclonic_mask = sla_grid < -self.ssh_threshold
        labeled_c, num_c = ndimage.label(cyclonic_mask)
        
        for label_id in range(1, num_c + 1):
            eddy = self._extract_eddy(
                sla_grid, labeled_c == label_id,
                lat_range, lon_range, lat_step, lon_step,
                EddyType.CYCLONIC
            )
            if eddy:
                eddies.append(eddy)
        
        # 按強度排序
        eddies.sort(key=lambda e: e.intensity, reverse=True)
        
        return EddyDetectionResult(
            eddies=eddies,
            sla_field=sla_grid,
            metadata={
                "threshold_m": self.ssh_threshold,
                "lat_range": lat_range,
                "lon_range": lon_range
            }
        )
    
    def _extract_eddy(
        self,
        sla_grid: np.ndarray,
        mask: np.ndarray,
        lat_range: Tuple[float, float],
        lon_range: Tuple[float, float],
        lat_step: float,
        lon_step: float,
        eddy_type: EddyType
    ) -> Optional[Eddy]:
        """
        從標記區域提取渦旋信息
        """
        coords = np.argwhere(mask)
        
        if len(coords) < 4:  # 太小
            return None
        
        # 計算中心 (質心)
        center_row = coords[:, 0].mean()
        center_col = coords[:, 1].mean()
        
        center_lat = lat_range[0] + center_row * lat_step
        center_lon = lon_range[0] + center_col * lon_step
        
        # 估算半徑
        area_pixels = len(coords)
        pixel_area = lat_step * lon_step * 111**2  # 約 km²
        area_km2 = area_pixels * pixel_area
        radius_km = np.sqrt(area_km2 / np.pi)
        
        if radius_km < self.min_radius_km or radius_km > self.max_radius_km:
            return None
        
        # 提取 SLA 值
        sla_values = sla_grid[mask]
        
        if eddy_type == EddyType.ANTICYCLONIC:
            ssh_anomaly = float(np.max(sla_values))
        else:
            ssh_anomaly = float(np.min(sla_values))
        
        # 計算強度 (基於 SLA 和大小)
        intensity = min(100, abs(ssh_anomaly) * 500 + radius_km * 0.2)
        
        return Eddy(
            eddy_type=eddy_type,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            ssh_anomaly=ssh_anomaly,
            intensity=intensity
        )
    
    def get_eddy_score(
        self,
        lat: float,
        lon: float,
        eddies: List[Eddy],
        fishing_preference: str = "edge"
    ) -> float:
        """
        計算位置的渦旋分數
        
        Args:
            lat, lon: 位置座標
            eddies: 渦旋列表
            fishing_preference: 偏好位置
                - "edge": 渦旋邊緣 (鋒面、餌料)
                - "center": 渦旋中心 (大型魚)
                - "cyclonic": 氣旋渦旋優先
                - "anticyclonic": 反氣旋優先
                
        Returns:
            渦旋分數 (0-100)
        """
        if not eddies:
            return 0.0
        
        best_score = 0.0
        
        for eddy in eddies:
            # 計算到渦旋中心的距離
            dist_km = self._haversine(
                lat, lon,
                eddy.center_lat, eddy.center_lon
            )
            
            # 計算相對距離 (距離/半徑)
            relative_dist = dist_km / max(1, eddy.radius_km)
            
            # 根據偏好計算分數
            if fishing_preference == "edge":
                # 邊緣最佳 (相對距離 0.7-1.3)
                if 0.7 <= relative_dist <= 1.3:
                    position_score = 100
                elif relative_dist < 0.7:
                    position_score = relative_dist / 0.7 * 70
                elif relative_dist < 2.0:
                    position_score = (2.0 - relative_dist) / 0.7 * 70
                else:
                    position_score = 0
                    
            elif fishing_preference == "center":
                # 中心最佳
                if relative_dist <= 0.5:
                    position_score = 100
                elif relative_dist <= 1.0:
                    position_score = (1.0 - relative_dist) * 2 * 100
                else:
                    position_score = 0
                    
            elif fishing_preference == "cyclonic":
                if not eddy.is_cyclonic:
                    continue
                position_score = max(0, 100 - relative_dist * 50)
                
            elif fishing_preference == "anticyclonic":
                if eddy.is_cyclonic:
                    continue
                position_score = max(0, 100 - relative_dist * 50)
                
            else:
                position_score = max(0, 100 - relative_dist * 50)
            
            # 渦旋強度加成
            intensity_factor = eddy.intensity / 100
            score = position_score * (0.5 + 0.5 * intensity_factor)
            
            best_score = max(best_score, score)
        
        return best_score
    
    def _haversine(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """計算兩點距離 (km)"""
        R = 6371.0
        
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c


def detect_eddies(
    ssh_data: pd.DataFrame,
    ssh_threshold: float = 0.05
) -> EddyDetectionResult:
    """
    便捷函數：檢測渦旋
    
    Args:
        ssh_data: SSH 數據 DataFrame
        ssh_threshold: SLA 閾值 (m)
        
    Returns:
        EddyDetectionResult
    """
    detector = EddyDetector(ssh_threshold=ssh_threshold)
    return detector.detect_from_dataframe(ssh_data)
