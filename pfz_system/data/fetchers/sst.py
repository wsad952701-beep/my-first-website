"""
SST (Sea Surface Temperature) 數據獲取器

獲取海表溫度數據，支持多個數據源：
- NOAA CoastWatch ERDDAP (JPL MUR SST)
- Copernicus Marine Service
- Open-Meteo Marine API
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

import requests
import pandas as pd
import numpy as np

from .base import (
    BaseDataFetcher,
    BoundingBox,
    TimeRange,
    FetchResult,
    haversine_distance
)

logger = logging.getLogger(__name__)


@dataclass
class SSTDataPoint:
    """SST 數據點"""
    lat: float
    lon: float
    time: datetime
    sst: float  # °C
    quality: Optional[float] = None


class SSTFetcher(BaseDataFetcher):
    """
    海表溫度數據獲取器
    
    從 ERDDAP 服務獲取高分辨率 SST 數據。
    
    Attributes:
        dataset_id: ERDDAP 數據集 ID
        base_url: ERDDAP 服務 URL
    
    Example:
        >>> fetcher = SSTFetcher()
        >>> bbox = BoundingBox(lat_min=20, lat_max=26, lon_min=118, lon_max=123)
        >>> result = fetcher.fetch(bbox)
        >>> print(result.data.shape)
    """
    
    # NOAA CoastWatch ERDDAP
    BASE_URL = "https://coastwatch.pfeg.noaa.gov/erddap"
    DATASET_ID = "jplMURSST41"  # JPL MUR SST 1km 分辨率
    
    # 備用：Open-Meteo Marine API (較低分辨率但更穩定)
    BACKUP_URL = "https://marine-api.open-meteo.com/v1/marine"
    
    def __init__(
        self,
        dataset_id: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 SST 獲取器
        
        Args:
            dataset_id: ERDDAP 數據集 ID
            base_url: ERDDAP 服務 URL
            **kwargs: 傳遞給 BaseDataFetcher 的參數
        """
        super().__init__(**kwargs)
        self.dataset_id = dataset_id or self.DATASET_ID
        self.base_url = base_url or self.BASE_URL
    
    def fetch(
        self,
        bbox: BoundingBox,
        time_range: Optional[TimeRange] = None
    ) -> FetchResult[pd.DataFrame]:
        """
        獲取區域 SST 數據
        
        Args:
            bbox: 地理邊界框
            time_range: 時間範圍，默認為最近 3 天
            
        Returns:
            包含 SST 數據的 FetchResult
        """
        # 默認時間範圍
        if time_range is None:
            time_range = TimeRange.last_n_days(3)
        
        # 檢查快取
        cache_key = self._generate_cache_key(
            bbox.lat_min, bbox.lat_max, bbox.lon_min, bbox.lon_max,
            time_range.start.date().isoformat()
        )
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info(f"SST data loaded from cache")
            return FetchResult(
                data=pd.DataFrame(cached),
                source=f"cache:{self.dataset_id}",
                is_cached=True
            )
        
        # 嘗試從 ERDDAP 獲取
        try:
            df = self._fetch_from_erddap(bbox, time_range)
            if df is not None and not df.empty:
                self.cache.set(cache_key, df.to_dict("records"))
                return FetchResult(
                    data=df,
                    source=f"erddap:{self.dataset_id}",
                    metadata={"resolution_km": 1.0}
                )
        except Exception as e:
            logger.warning(f"ERDDAP fetch failed: {e}")
        
        # 備用：從 Open-Meteo 獲取
        try:
            df = self._fetch_from_openmeteo(bbox)
            if df is not None and not df.empty:
                return FetchResult(
                    data=df,
                    source="open-meteo:marine",
                    metadata={"resolution_km": 5.0}
                )
        except Exception as e:
            logger.error(f"Open-Meteo fetch failed: {e}")
        
        # 返回空數據
        return FetchResult(
            data=pd.DataFrame(),
            source="none",
            metadata={"error": "All data sources failed"}
        )
    
    def _fetch_from_erddap(
        self,
        bbox: BoundingBox,
        time_range: TimeRange
    ) -> Optional[pd.DataFrame]:
        """
        從 ERDDAP 獲取 SST 數據
        
        Args:
            bbox: 邊界框
            time_range: 時間範圍
            
        Returns:
            SST 數據 DataFrame
        """
        # 構建 ERDDAP griddap URL
        url = f"{self.base_url}/griddap/{self.dataset_id}.json"
        
        # 格式化時間和座標
        time_start = time_range.start.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_end = time_range.end.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # ERDDAP 查詢語法
        query = (
            f"analysed_sst[({time_start}):1:({time_end})]"
            f"[({bbox.lat_min}):1:({bbox.lat_max})]"
            f"[({bbox.lon_min}):1:({bbox.lon_max})]"
        )
        
        params = {"query": query}
        
        response = self._make_request(url, params)
        data = response.json()
        
        # 解析 ERDDAP JSON 響應
        table = data.get("table", {})
        column_names = table.get("columnNames", [])
        rows = table.get("rows", [])
        
        if not rows:
            return None
        
        df = pd.DataFrame(rows, columns=column_names)
        
        # 標準化列名
        df = df.rename(columns={
            "time": "time",
            "latitude": "lat",
            "longitude": "lon",
            "analysed_sst": "sst"
        })
        
        # 轉換溫度單位 (Kelvin -> Celsius)
        if df["sst"].mean() > 200:  # 可能是 Kelvin
            df["sst"] = df["sst"] - 273.15
        
        df["time"] = pd.to_datetime(df["time"])
        
        return df
    
    def _fetch_from_openmeteo(
        self,
        bbox: BoundingBox
    ) -> Optional[pd.DataFrame]:
        """
        從 Open-Meteo Marine API 獲取 SST 數據
        
        Args:
            bbox: 邊界框
            
        Returns:
            SST 數據 DataFrame
        """
        # Open-Meteo Marine 使用單點查詢，需要網格化
        lat_center, lon_center = bbox.center()
        
        # 生成網格點
        lat_step = 0.25
        lon_step = 0.25
        
        lats = np.arange(bbox.lat_min, bbox.lat_max + lat_step, lat_step)
        lons = np.arange(bbox.lon_min, bbox.lon_max + lon_step, lon_step)
        
        # 限制點數
        if len(lats) * len(lons) > 100:
            # 降低分辨率
            lats = np.linspace(bbox.lat_min, bbox.lat_max, 10)
            lons = np.linspace(bbox.lon_min, bbox.lon_max, 10)
        
        records = []
        
        for lat in lats:
            for lon in lons:
                try:
                    params = {
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": "sea_surface_temperature",
                        "forecast_days": 1,
                        "timezone": "UTC"
                    }
                    
                    response = self.session.get(
                        self.BACKUP_URL,
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        hourly = data.get("hourly", {})
                        times = hourly.get("time", [])
                        sst_values = hourly.get("sea_surface_temperature", [])
                        
                        if times and sst_values:
                            # 取最新值
                            records.append({
                                "lat": lat,
                                "lon": lon,
                                "time": times[-1],
                                "sst": sst_values[-1]
                            })
                            
                except Exception as e:
                    logger.debug(f"Point fetch failed ({lat}, {lon}): {e}")
                    continue
        
        if not records:
            return None
        
        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"])
        
        return df
    
    def get_latest_sst(
        self,
        lat: float,
        lon: float
    ) -> Optional[float]:
        """
        獲取單點最新 SST
        
        Args:
            lat: 緯度
            lon: 經度
            
        Returns:
            SST 值 (°C)，失敗則返回 None
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "sea_surface_temperature",
                "forecast_days": 1,
                "timezone": "UTC"
            }
            
            response = self.session.get(
                self.BACKUP_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            sst_values = data.get("hourly", {}).get("sea_surface_temperature", [])
            
            if sst_values:
                # 過濾 None 值並取平均
                valid = [v for v in sst_values if v is not None]
                if valid:
                    return sum(valid) / len(valid)
            
        except Exception as e:
            logger.debug(f"SST point fetch failed: {e}")
        
        return None
    
    def calculate_gradient(
        self,
        sst_data: pd.DataFrame,
        resolution_km: float = 5.0
    ) -> pd.DataFrame:
        """
        計算 SST 梯度
        
        Args:
            sst_data: SST 數據 DataFrame (需有 lat, lon, sst 列)
            resolution_km: 數據分辨率 (km)
            
        Returns:
            添加 gradient 列的 DataFrame
        """
        if sst_data.empty or "sst" not in sst_data.columns:
            return sst_data
        
        df = sst_data.copy()
        gradients = []
        
        for idx, row in df.iterrows():
            lat, lon, sst = row["lat"], row["lon"], row["sst"]
            
            # 找鄰近點
            neighbors = df[
                (df["lat"].between(lat - 0.5, lat + 0.5)) &
                (df["lon"].between(lon - 0.5, lon + 0.5)) &
                (df.index != idx)
            ]
            
            if len(neighbors) < 2:
                gradients.append(0.0)
                continue
            
            # 計算與鄰近點的溫度差
            max_gradient = 0.0
            for _, neighbor in neighbors.iterrows():
                dist = haversine_distance(lat, lon, neighbor["lat"], neighbor["lon"])
                if dist > 0:
                    gradient = abs(sst - neighbor["sst"]) / dist
                    max_gradient = max(max_gradient, gradient)
            
            gradients.append(max_gradient)
        
        df["gradient"] = gradients
        
        return df
