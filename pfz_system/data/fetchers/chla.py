"""
Chlorophyll-a 數據獲取器

獲取葉綠素濃度數據，用於評估初級生產力：
- MODIS Aqua/Terra
- Copernicus Marine Service
- NOAA CoastWatch ERDDAP
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
    FetchResult
)

logger = logging.getLogger(__name__)


class ChlaFetcher(BaseDataFetcher):
    """
    葉綠素 a 數據獲取器
    
    從 ERDDAP 服務獲取衛星遙測葉綠素數據。
    
    Attributes:
        dataset_id: ERDDAP 數據集 ID
        base_url: ERDDAP 服務 URL
    
    Example:
        >>> fetcher = ChlaFetcher()
        >>> bbox = BoundingBox(lat_min=20, lat_max=26, lon_min=118, lon_max=123)
        >>> result = fetcher.fetch(bbox)
        >>> print(result.data.head())
    """
    
    # NOAA CoastWatch ERDDAP
    BASE_URL = "https://coastwatch.pfeg.noaa.gov/erddap"
    
    # 可用數據集 (按優先順序)
    DATASETS = [
        {
            "id": "erdMH1chla8day",
            "name": "MODIS Aqua 8-day Chlorophyll",
            "resolution_km": 4.0,
            "variable": "chlorophyll"
        },
        {
            "id": "erdMH1chlamday",
            "name": "MODIS Aqua Monthly Chlorophyll",
            "resolution_km": 4.0,
            "variable": "chlorophyll"
        },
        {
            "id": "nesdisVHNSQchlaMonthly",
            "name": "VIIRS Monthly Chlorophyll",
            "resolution_km": 4.0,
            "variable": "chlor_a"
        }
    ]
    
    def __init__(
        self,
        dataset_id: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 Chl-a 獲取器
        
        Args:
            dataset_id: ERDDAP 數據集 ID
            base_url: ERDDAP 服務 URL
            **kwargs: 傳遞給 BaseDataFetcher 的參數
        """
        super().__init__(**kwargs)
        self.base_url = base_url or self.BASE_URL
        
        # 設定數據集
        if dataset_id:
            self.current_dataset = next(
                (d for d in self.DATASETS if d["id"] == dataset_id),
                self.DATASETS[0]
            )
        else:
            self.current_dataset = self.DATASETS[0]
    
    def fetch(
        self,
        bbox: BoundingBox,
        time_range: Optional[TimeRange] = None
    ) -> FetchResult[pd.DataFrame]:
        """
        獲取區域葉綠素數據
        
        Args:
            bbox: 地理邊界框
            time_range: 時間範圍，默認為最近 8 天
            
        Returns:
            包含 Chl-a 數據的 FetchResult
        """
        # 默認時間範圍 (8天合成產品)
        if time_range is None:
            time_range = TimeRange.last_n_days(8)
        
        # 檢查快取
        cache_key = self._generate_cache_key(
            bbox.lat_min, bbox.lat_max, bbox.lon_min, bbox.lon_max,
            time_range.start.date().isoformat()
        )
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Chl-a data loaded from cache")
            return FetchResult(
                data=pd.DataFrame(cached),
                source=f"cache:{self.current_dataset['id']}",
                is_cached=True
            )
        
        # 嘗試各數據集
        for dataset in self.DATASETS:
            try:
                df = self._fetch_from_erddap(bbox, time_range, dataset)
                if df is not None and not df.empty:
                    self.cache.set(cache_key, df.to_dict("records"))
                    return FetchResult(
                        data=df,
                        source=f"erddap:{dataset['id']}",
                        metadata={"resolution_km": dataset["resolution_km"]}
                    )
            except Exception as e:
                logger.debug(f"Dataset {dataset['id']} failed: {e}")
                continue
        
        # 嘗試模擬數據 (用於測試)
        logger.warning("All Chl-a sources failed, generating synthetic data")
        df = self._generate_synthetic(bbox)
        
        return FetchResult(
            data=df,
            source="synthetic",
            metadata={"warning": "synthetic data for testing"}
        )
    
    def _fetch_from_erddap(
        self,
        bbox: BoundingBox,
        time_range: TimeRange,
        dataset: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        從 ERDDAP 獲取 Chl-a 數據
        
        Args:
            bbox: 邊界框
            time_range: 時間範圍
            dataset: 數據集配置
            
        Returns:
            Chl-a 數據 DataFrame
        """
        url = f"{self.base_url}/griddap/{dataset['id']}.json"
        
        # 格式化時間
        time_start = time_range.start.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_end = time_range.end.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        variable = dataset["variable"]
        
        # ERDDAP 查詢
        query = (
            f"{variable}[({time_start}):1:({time_end})]"
            f"[({bbox.lat_max}):1:({bbox.lat_min})]"  # 注意：緯度可能需要反向
            f"[({bbox.lon_min}):1:({bbox.lon_max})]"
        )
        
        params = {"query": query}
        
        response = self._make_request(url, params)
        data = response.json()
        
        # 解析響應
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
            variable: "chla"
        })
        
        # 過濾無效值
        df = df[df["chla"].notna()]
        df = df[df["chla"] >= 0]  # Chl-a 不能為負
        df = df[df["chla"] < 100]  # 過濾異常高值
        
        df["time"] = pd.to_datetime(df["time"])
        
        return df
    
    def _generate_synthetic(
        self,
        bbox: BoundingBox,
        resolution: float = 0.25
    ) -> pd.DataFrame:
        """
        生成模擬 Chl-a 數據 (用於測試)
        
        Args:
            bbox: 邊界框
            resolution: 網格分辨率 (度)
            
        Returns:
            模擬數據 DataFrame
        """
        lats = np.arange(bbox.lat_min, bbox.lat_max, resolution)
        lons = np.arange(bbox.lon_min, bbox.lon_max, resolution)
        
        records = []
        now = datetime.utcnow()
        
        for lat in lats:
            for lon in lons:
                # 模擬空間變異
                base_chla = 0.3
                lat_factor = 0.1 * np.sin(np.radians(lat * 10))
                lon_factor = 0.1 * np.cos(np.radians(lon * 5))
                noise = np.random.normal(0, 0.05)
                
                chla = max(0.01, base_chla + lat_factor + lon_factor + noise)
                
                records.append({
                    "lat": lat,
                    "lon": lon,
                    "time": now,
                    "chla": round(chla, 3)
                })
        
        return pd.DataFrame(records)
    
    def get_productivity_class(
        self,
        chla: float
    ) -> str:
        """
        根據 Chl-a 濃度判定生產力等級
        
        Args:
            chla: 葉綠素濃度 (mg/m³)
            
        Returns:
            生產力等級
        """
        if chla < 0.1:
            return "oligotrophic"  # 貧營養
        elif chla < 0.3:
            return "mesotrophic"   # 中營養
        elif chla < 1.0:
            return "eutrophic"     # 富營養
        else:
            return "hypereutrophic"  # 超富營養
    
    def calculate_bloom_probability(
        self,
        chla_data: pd.DataFrame,
        threshold: float = 1.0
    ) -> pd.DataFrame:
        """
        計算藻華發生機率
        
        Args:
            chla_data: Chl-a 數據 DataFrame
            threshold: 藻華閾值 (mg/m³)
            
        Returns:
            添加 bloom_prob 列的 DataFrame
        """
        if chla_data.empty or "chla" not in chla_data.columns:
            return chla_data
        
        df = chla_data.copy()
        
        # 簡化的藻華機率計算
        df["bloom_prob"] = np.clip(df["chla"] / threshold, 0, 1) * 100
        df["productivity_class"] = df["chla"].apply(self.get_productivity_class)
        
        return df
