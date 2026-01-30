"""
PFZ Data Fetchers Module

提供海洋數據獲取功能。
"""

try:
    from .base import (
        BaseDataFetcher,
        BoundingBox,
        TimeRange,
        FetchResult,
        CacheManager,
        validate_coordinates,
        haversine_distance
    )
    from .sst import SSTFetcher
    from .chla import ChlaFetcher
    from .ssh import SSHFetcher
except ImportError:
    from base import (
        BaseDataFetcher,
        BoundingBox,
        TimeRange,
        FetchResult,
        CacheManager,
        validate_coordinates,
        haversine_distance
    )
    from sst import SSTFetcher
    from chla import ChlaFetcher
    from ssh import SSHFetcher

__all__ = [
    # Base
    "BaseDataFetcher",
    "BoundingBox",
    "TimeRange",
    "FetchResult",
    "CacheManager",
    "validate_coordinates",
    "haversine_distance",
    # Fetchers
    "SSTFetcher",
    "ChlaFetcher",
    "SSHFetcher",
]
