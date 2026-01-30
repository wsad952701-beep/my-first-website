"""
Data Fetchers Base Module

提供數據獲取器的基礎類與通用工具，包括：
- 抽象基類
- 快取機制
- 重試邏輯
- 數據驗證
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TypeVar, Generic
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import logging
import time

import requests
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class BoundingBox:
    """
    地理邊界框
    
    Attributes:
        lat_min: 最小緯度
        lat_max: 最大緯度
        lon_min: 最小經度
        lon_max: 最大經度
    """
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    
    def __post_init__(self):
        """驗證邊界有效性"""
        if not (-90 <= self.lat_min <= self.lat_max <= 90):
            raise ValueError(f"Invalid latitudes: {self.lat_min}, {self.lat_max}")
        if not (-180 <= self.lon_min <= self.lon_max <= 180):
            raise ValueError(f"Invalid longitudes: {self.lon_min}, {self.lon_max}")
    
    def center(self) -> tuple:
        """返回中心點"""
        return (
            (self.lat_min + self.lat_max) / 2,
            (self.lon_min + self.lon_max) / 2
        )
    
    def to_dict(self) -> Dict[str, float]:
        """轉換為字典"""
        return {
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "lon_min": self.lon_min,
            "lon_max": self.lon_max
        }
    
    def expand(self, degrees: float) -> "BoundingBox":
        """擴展邊界框"""
        return BoundingBox(
            lat_min=max(-90, self.lat_min - degrees),
            lat_max=min(90, self.lat_max + degrees),
            lon_min=max(-180, self.lon_min - degrees),
            lon_max=min(180, self.lon_max + degrees)
        )


@dataclass
class TimeRange:
    """
    時間範圍
    
    Attributes:
        start: 開始時間
        end: 結束時間
    """
    start: datetime
    end: datetime
    
    def __post_init__(self):
        """驗證時間有效性"""
        if self.start > self.end:
            raise ValueError(f"Start time must be before end time: {self.start} > {self.end}")
    
    @classmethod
    def last_n_days(cls, days: int) -> "TimeRange":
        """創建過去 N 天的時間範圍"""
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        return cls(start=start, end=end)
    
    @classmethod
    def today(cls) -> "TimeRange":
        """創建今天的時間範圍"""
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
        return cls(start=start, end=end)
    
    def to_dict(self) -> Dict[str, str]:
        """轉換為字典"""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat()
        }


@dataclass
class FetchResult(Generic[T]):
    """
    數據獲取結果
    
    Attributes:
        data: 獲取的數據
        source: 數據來源
        timestamp: 獲取時間
        is_cached: 是否來自快取
        metadata: 額外元數據
    """
    data: T
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """檢查數據是否有效"""
        return self.data is not None


class CacheManager:
    """
    快取管理器
    
    提供基於檔案的數據快取，支持 TTL 過期機制。
    
    Example:
        >>> cache = CacheManager(cache_dir=Path("./cache"), ttl_hours=6)
        >>> cache.set("my_key", {"data": [1, 2, 3]})
        >>> data = cache.get("my_key")
    """
    
    def __init__(
        self,
        cache_dir: Path,
        ttl_hours: int = 6,
        enabled: bool = True
    ):
        """
        初始化快取管理器
        
        Args:
            cache_dir: 快取目錄
            ttl_hours: 快取存活時間 (小時)
            enabled: 是否啟用快取
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.enabled = enabled
        
        if enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """生成快取檔案路徑"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取數據
        
        Args:
            key: 快取鍵
            
        Returns:
            快取數據，不存在或過期則返回 None
        """
        if not self.enabled:
            return None
        
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            # 檢查過期
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.utcnow() - cached_time > timedelta(hours=self.ttl_hours):
                cache_path.unlink()
                return None
            
            return cached["data"]
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None
    
    def set(self, key: str, data: Any) -> bool:
        """
        設置快取數據
        
        Args:
            key: 快取鍵
            data: 要快取的數據
            
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "key": key,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data
                }, f)
            return True
            
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")
            return False
    
    def clear(self) -> int:
        """
        清除所有快取
        
        Returns:
            清除的檔案數量
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count


class BaseDataFetcher(ABC):
    """
    數據獲取器抽象基類
    
    提供統一的數據獲取介面與通用功能。
    
    Subclasses must implement:
        - fetch(): 實際的數據獲取邏輯
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cache_enabled: bool = True,
        cache_ttl_hours: int = 6
    ):
        """
        初始化獲取器
        
        Args:
            timeout: 請求超時時間 (秒)
            max_retries: 最大重試次數
            retry_delay: 重試間隔基礎時間 (秒)
            cache_enabled: 是否啟用快取
            cache_ttl_hours: 快取存活時間 (小時)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PFZ-System/1.0"
        })
        
        self.cache = CacheManager(
            cache_dir=Path("./cache") / self.__class__.__name__.lower(),
            ttl_hours=cache_ttl_hours,
            enabled=cache_enabled
        )
    
    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET"
    ) -> requests.Response:
        """
        發送 HTTP 請求，帶自動重試
        
        Args:
            url: 請求 URL
            params: 查詢參數
            method: HTTP 方法
            
        Returns:
            響應對象
            
        Raises:
            requests.RequestException: 所有重試失敗後
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=params, timeout=self.timeout)
                else:
                    response = self.session.post(url, json=params, timeout=self.timeout)
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
        
        raise last_exception or requests.RequestException("Unknown error")
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """
        生成快取鍵
        
        Args:
            *args, **kwargs: 用於生成鍵的參數
            
        Returns:
            快取鍵字串
        """
        key_parts = [self.__class__.__name__]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "_".join(key_parts)
    
    @abstractmethod
    def fetch(
        self,
        bbox: BoundingBox,
        time_range: Optional[TimeRange] = None
    ) -> FetchResult:
        """
        獲取數據
        
        Args:
            bbox: 地理邊界框
            time_range: 時間範圍 (可選)
            
        Returns:
            FetchResult 數據結果
        """
        pass
    
    def fetch_point(
        self,
        lat: float,
        lon: float,
        time_range: Optional[TimeRange] = None
    ) -> FetchResult:
        """
        獲取單點數據
        
        Args:
            lat: 緯度
            lon: 經度
            time_range: 時間範圍
            
        Returns:
            FetchResult 數據結果
        """
        # 創建一個小的邊界框
        bbox = BoundingBox(
            lat_min=lat - 0.1,
            lat_max=lat + 0.1,
            lon_min=lon - 0.1,
            lon_max=lon + 0.1
        )
        return self.fetch(bbox, time_range)


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    驗證座標有效性
    
    Args:
        lat: 緯度
        lon: 經度
        
    Returns:
        是否有效
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    計算兩點間的大圓距離 (公里)
    
    Args:
        lat1, lon1: 第一點座標
        lat2, lon2: 第二點座標
        
    Returns:
        距離 (公里)
    """
    R = 6371.0  # 地球半徑 (km)
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c
