"""
海洋熱鋒面檢測算法

基於 SST 梯度識別海洋鋒面，這些區域通常：
- 營養鹽豐富
- 餌料魚聚集
- 捕食者活躍

算法方法：
1. Sobel 梯度計算
2. 自適應閾值
3. 鋒面線追蹤
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.interpolate import griddata

logger = logging.getLogger(__name__)


@dataclass
class FrontSegment:
    """鋒面線段"""
    coordinates: List[Tuple[float, float]]  # [(lat, lon), ...]
    gradient_mean: float                     # 平均梯度 (°C/km)
    gradient_max: float                      # 最大梯度
    length_km: float                         # 長度 (km)
    
    @property
    def start(self) -> Tuple[float, float]:
        """起點"""
        return self.coordinates[0] if self.coordinates else (0, 0)
    
    @property
    def end(self) -> Tuple[float, float]:
        """終點"""
        return self.coordinates[-1] if self.coordinates else (0, 0)


@dataclass
class FrontDetectionResult:
    """鋒面檢測結果"""
    fronts: List[FrontSegment]
    gradient_field: np.ndarray
    detection_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def front_count(self) -> int:
        """鋒面數量"""
        return len(self.fronts)
    
    @property
    def total_length_km(self) -> float:
        """總長度 (km)"""
        return sum(f.length_km for f in self.fronts)


class FrontDetector:
    """
    海洋鋒面檢測器
    
    使用 Sobel 算子計算 SST 梯度，識別強梯度區域作為鋒面。
    
    Attributes:
        gradient_threshold: 梯度閾值 (°C/km)
        min_length_km: 最短鋒面長度 (km)
    
    Example:
        >>> detector = FrontDetector(gradient_threshold=0.3)
        >>> sst_data = np.random.rand(100, 100) * 5 + 25
        >>> result = detector.detect_from_grid(sst_data, lat_range, lon_range)
        >>> print(f"Found {result.front_count} fronts")
    """
    
    def __init__(
        self,
        gradient_threshold: float = 0.5,
        min_length_km: float = 10.0,
        resolution_km: float = 4.0
    ):
        """
        初始化鋒面檢測器
        
        Args:
            gradient_threshold: 梯度閾值 (°C/km)，超過此值視為鋒面
            min_length_km: 最短鋒面長度 (km)
            resolution_km: 數據分辨率 (km)
        """
        self.gradient_threshold = gradient_threshold
        self.min_length_km = min_length_km
        self.resolution_km = resolution_km
    
    def detect_from_dataframe(
        self,
        sst_data: pd.DataFrame,
        lat_col: str = "lat",
        lon_col: str = "lon",
        sst_col: str = "sst"
    ) -> FrontDetectionResult:
        """
        從 DataFrame 檢測鋒面
        
        Args:
            sst_data: SST 數據 DataFrame
            lat_col, lon_col, sst_col: 列名
            
        Returns:
            FrontDetectionResult
        """
        if sst_data.empty:
            return FrontDetectionResult(fronts=[], gradient_field=np.array([]))
        
        df = sst_data.copy()
        
        # 創建規則網格
        lats = np.sort(df[lat_col].unique())
        lons = np.sort(df[lon_col].unique())
        
        # 插值到規則網格
        grid_lat, grid_lon = np.meshgrid(lats, lons, indexing='ij')
        
        points = df[[lat_col, lon_col]].values
        values = df[sst_col].values
        
        sst_grid = griddata(points, values, (grid_lat, grid_lon), method='linear')
        
        # 填充 NaN
        sst_grid = np.nan_to_num(sst_grid, nan=np.nanmean(values))
        
        lat_range = (lats.min(), lats.max())
        lon_range = (lons.min(), lons.max())
        
        return self.detect_from_grid(sst_grid, lat_range, lon_range)
    
    def detect_from_grid(
        self,
        sst_grid: np.ndarray,
        lat_range: Tuple[float, float],
        lon_range: Tuple[float, float]
    ) -> FrontDetectionResult:
        """
        從網格數據檢測鋒面
        
        Args:
            sst_grid: 2D SST 網格 (lat x lon)
            lat_range: 緯度範圍 (min, max)
            lon_range: 經度範圍 (min, max)
            
        Returns:
            FrontDetectionResult
        """
        if sst_grid.size == 0:
            return FrontDetectionResult(fronts=[], gradient_field=np.array([]))
        
        # 計算梯度
        gradient_field = self._calculate_gradient(sst_grid)
        
        # 識別鋒面像素
        front_mask = gradient_field > self.gradient_threshold
        
        # 連通區域標記
        labeled, num_features = ndimage.label(front_mask)
        
        # 提取鋒面線段
        fronts = []
        nrows, ncols = sst_grid.shape
        
        for label_id in range(1, num_features + 1):
            region_mask = labeled == label_id
            
            # 獲取區域坐標
            coords = np.argwhere(region_mask)
            
            if len(coords) < 3:
                continue
            
            # 轉換為地理坐標
            lat_step = (lat_range[1] - lat_range[0]) / max(1, nrows - 1)
            lon_step = (lon_range[1] - lon_range[0]) / max(1, ncols - 1)
            
            geo_coords = [
                (lat_range[0] + r * lat_step, lon_range[0] + c * lon_step)
                for r, c in coords
            ]
            
            # 計算長度
            length_km = self._calculate_length(geo_coords)
            
            if length_km < self.min_length_km:
                continue
            
            # 提取梯度統計
            region_gradients = gradient_field[region_mask]
            
            front = FrontSegment(
                coordinates=geo_coords,
                gradient_mean=float(np.mean(region_gradients)),
                gradient_max=float(np.max(region_gradients)),
                length_km=length_km
            )
            
            fronts.append(front)
        
        # 按梯度排序
        fronts.sort(key=lambda f: f.gradient_max, reverse=True)
        
        return FrontDetectionResult(
            fronts=fronts,
            gradient_field=gradient_field,
            metadata={
                "threshold": self.gradient_threshold,
                "resolution_km": self.resolution_km,
                "lat_range": lat_range,
                "lon_range": lon_range
            }
        )
    
    def _calculate_gradient(self, sst_grid: np.ndarray) -> np.ndarray:
        """
        計算 SST 梯度場
        
        使用 Sobel 算子計算水平和垂直方向的梯度。
        
        Args:
            sst_grid: SST 網格
            
        Returns:
            梯度場 (°C/km)
        """
        # Sobel 算子計算梯度
        dy = ndimage.sobel(sst_grid, axis=0, mode='constant')  # 緯度方向
        dx = ndimage.sobel(sst_grid, axis=1, mode='constant')  # 經度方向
        
        # 計算梯度大小
        gradient_magnitude = np.sqrt(dx**2 + dy**2)
        
        # 轉換為 °C/km
        gradient_per_km = gradient_magnitude / self.resolution_km
        
        return gradient_per_km
    
    def _calculate_length(
        self,
        coords: List[Tuple[float, float]]
    ) -> float:
        """
        計算鋒面線段長度
        
        Args:
            coords: 地理坐標列表
            
        Returns:
            長度 (km)
        """
        if len(coords) < 2:
            return 0.0
        
        total = 0.0
        R = 6371.0  # 地球半徑 (km)
        
        for i in range(len(coords) - 1):
            lat1, lon1 = np.radians(coords[i])
            lat2, lon2 = np.radians(coords[i + 1])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            
            total += R * c
        
        return total
    
    def get_front_score(
        self,
        lat: float,
        lon: float,
        fronts: List[FrontSegment],
        max_distance_km: float = 50.0
    ) -> float:
        """
        計算位置的鋒面分數
        
        Args:
            lat, lon: 位置座標
            fronts: 鋒面列表
            max_distance_km: 最大影響距離
            
        Returns:
            鋒面分數 (0-100)
        """
        if not fronts:
            return 0.0
        
        min_distance = float('inf')
        max_gradient = 0.0
        
        R = 6371.0
        
        for front in fronts:
            for front_lat, front_lon in front.coordinates:
                # 簡化距離計算
                dlat = np.radians(lat - front_lat)
                dlon = np.radians(lon - front_lon)
                lat1 = np.radians(lat)
                lat2 = np.radians(front_lat)
                
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                dist = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                
                if dist < min_distance:
                    min_distance = dist
                    max_gradient = front.gradient_max
        
        if min_distance > max_distance_km:
            return 0.0
        
        # 距離越近分數越高
        distance_score = 100 * (1 - min_distance / max_distance_km)
        
        # 梯度加成
        gradient_bonus = min(20, max_gradient * 10)
        
        return min(100, distance_score + gradient_bonus)


def detect_fronts(
    sst_data: pd.DataFrame,
    gradient_threshold: float = 0.5
) -> FrontDetectionResult:
    """
    便捷函數：檢測海洋鋒面
    
    Args:
        sst_data: SST 數據 DataFrame (需有 lat, lon, sst 列)
        gradient_threshold: 梯度閾值 (°C/km)
        
    Returns:
        FrontDetectionResult
    """
    detector = FrontDetector(gradient_threshold=gradient_threshold)
    return detector.detect_from_dataframe(sst_data)
