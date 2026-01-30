"""
SSH (Sea Surface Height) 數據獲取器

獲取海表高度數據，用於渦旋與海流分析：
- AVISO/Copernicus SSH
- NOAA SSH Products
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


class SSHFetcher(BaseDataFetcher):
    """
    海表高度數據獲取器
    
    從衛星高度計產品獲取 SSH 數據，用於識別：
    - 中尺度渦旋
    - 海流流場
    - 上升流區域
    
    Example:
        >>> fetcher = SSHFetcher()
        >>> bbox = BoundingBox(lat_min=20, lat_max=26, lon_min=118, lon_max=123)
        >>> result = fetcher.fetch(bbox)
    """
    
    # NOAA CoastWatch ERDDAP
    BASE_URL = "https://coastwatch.pfeg.noaa.gov/erddap"
    
    # 數據集選項
    DATASETS = [
        {
            "id": "nesdisSSH1day",
            "name": "NESDIS Daily SSH",
            "resolution_km": 4.0,
            "variable": "sea_surface_height"
        },
        {
            "id": "erdTAssh4day",
            "name": "AVISO 4-day SSH",
            "resolution_km": 25.0,
            "variable": "ssh"
        }
    ]
    
    def __init__(self, **kwargs):
        """初始化 SSH 獲取器"""
        super().__init__(**kwargs)
        self.current_dataset = self.DATASETS[0]
    
    def fetch(
        self,
        bbox: BoundingBox,
        time_range: Optional[TimeRange] = None
    ) -> FetchResult[pd.DataFrame]:
        """
        獲取區域 SSH 數據
        
        Args:
            bbox: 地理邊界框
            time_range: 時間範圍
            
        Returns:
            包含 SSH 數據的 FetchResult
        """
        if time_range is None:
            time_range = TimeRange.last_n_days(3)
        
        # 檢查快取
        cache_key = self._generate_cache_key(
            bbox.lat_min, bbox.lat_max, bbox.lon_min, bbox.lon_max,
            time_range.start.date().isoformat()
        )
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("SSH data loaded from cache")
            return FetchResult(
                data=pd.DataFrame(cached),
                source="cache",
                is_cached=True
            )
        
        # 嘗試從 ERDDAP 獲取
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
                logger.debug(f"SSH dataset {dataset['id']} failed: {e}")
        
        # 生成模擬數據
        logger.warning("SSH sources unavailable, generating synthetic data")
        df = self._generate_synthetic(bbox)
        
        return FetchResult(
            data=df,
            source="synthetic",
            metadata={"warning": "synthetic data"}
        )
    
    def _fetch_from_erddap(
        self,
        bbox: BoundingBox,
        time_range: TimeRange,
        dataset: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """從 ERDDAP 獲取 SSH 數據"""
        url = f"{self.BASE_URL}/griddap/{dataset['id']}.json"
        
        time_start = time_range.start.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_end = time_range.end.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        variable = dataset["variable"]
        
        query = (
            f"{variable}[({time_start}):1:({time_end})]"
            f"[({bbox.lat_min}):1:({bbox.lat_max})]"
            f"[({bbox.lon_min}):1:({bbox.lon_max})]"
        )
        
        params = {"query": query}
        
        response = self._make_request(url, params)
        data = response.json()
        
        table = data.get("table", {})
        column_names = table.get("columnNames", [])
        rows = table.get("rows", [])
        
        if not rows:
            return None
        
        df = pd.DataFrame(rows, columns=column_names)
        
        df = df.rename(columns={
            "time": "time",
            "latitude": "lat",
            "longitude": "lon",
            variable: "ssh"
        })
        
        df["time"] = pd.to_datetime(df["time"])
        df = df.dropna(subset=["ssh"])
        
        return df
    
    def _generate_synthetic(
        self,
        bbox: BoundingBox,
        resolution: float = 0.25
    ) -> pd.DataFrame:
        """生成模擬 SSH 數據"""
        lats = np.arange(bbox.lat_min, bbox.lat_max, resolution)
        lons = np.arange(bbox.lon_min, bbox.lon_max, resolution)
        
        records = []
        now = datetime.utcnow()
        
        # 模擬渦旋結構
        eddy_lat = (bbox.lat_min + bbox.lat_max) / 2
        eddy_lon = (bbox.lon_min + bbox.lon_max) / 2
        eddy_radius = 1.0  # 度
        eddy_amplitude = 0.15  # 米
        
        for lat in lats:
            for lon in lons:
                # 計算到渦旋中心距離
                dist = np.sqrt((lat - eddy_lat)**2 + (lon - eddy_lon)**2)
                
                # 高斯型渦旋
                ssh_eddy = eddy_amplitude * np.exp(-(dist / eddy_radius)**2)
                
                # 添加隨機噪聲
                noise = np.random.normal(0, 0.02)
                
                ssh = ssh_eddy + noise
                
                records.append({
                    "lat": lat,
                    "lon": lon,
                    "time": now,
                    "ssh": round(ssh, 4)
                })
        
        return pd.DataFrame(records)
    
    def calculate_sla(
        self,
        ssh_data: pd.DataFrame,
        reference_ssh: Optional[float] = None
    ) -> pd.DataFrame:
        """
        計算海表高度異常 (SLA)
        
        Args:
            ssh_data: SSH 數據 DataFrame
            reference_ssh: 參考 SSH 值，None 則使用平均值
            
        Returns:
            添加 sla 列的 DataFrame
        """
        if ssh_data.empty or "ssh" not in ssh_data.columns:
            return ssh_data
        
        df = ssh_data.copy()
        
        if reference_ssh is None:
            reference_ssh = df["ssh"].mean()
        
        df["sla"] = df["ssh"] - reference_ssh
        
        return df
    
    def identify_eddies(
        self,
        ssh_data: pd.DataFrame,
        threshold_m: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        識別渦旋區域
        
        Args:
            ssh_data: SSH 數據 DataFrame
            threshold_m: SLA 閾值 (米)
            
        Returns:
            渦旋列表 [{"type": "cyclonic/anticyclonic", "center": (lat, lon), ...}]
        """
        if ssh_data.empty or "ssh" not in ssh_data.columns:
            return []
        
        df = self.calculate_sla(ssh_data)
        
        eddies = []
        
        # 識別強正異常 (反氣旋渦旋)
        anticyclonic = df[df["sla"] > threshold_m]
        if not anticyclonic.empty:
            max_idx = anticyclonic["sla"].idxmax()
            center = anticyclonic.loc[max_idx]
            eddies.append({
                "type": "anticyclonic",
                "center_lat": center["lat"],
                "center_lon": center["lon"],
                "max_sla": center["sla"],
                "description": "暖心渦旋，下沉區"
            })
        
        # 識別強負異常 (氣旋渦旋)
        cyclonic = df[df["sla"] < -threshold_m]
        if not cyclonic.empty:
            min_idx = cyclonic["sla"].idxmin()
            center = cyclonic.loc[min_idx]
            eddies.append({
                "type": "cyclonic",
                "center_lat": center["lat"],
                "center_lon": center["lon"],
                "min_sla": center["sla"],
                "description": "冷心渦旋，上升流區"
            })
        
        return eddies
