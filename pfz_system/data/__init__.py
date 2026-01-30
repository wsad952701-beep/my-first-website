"""
PFZ Data Module

提供海洋數據獲取與處理功能。
"""

try:
    from .fetchers import (
        BaseDataFetcher,
        BoundingBox,
        TimeRange,
        FetchResult,
        SSTFetcher,
        ChlaFetcher,
        SSHFetcher
    )
except ImportError:
    from fetchers import (
        BaseDataFetcher,
        BoundingBox,
        TimeRange,
        FetchResult,
        SSTFetcher,
        ChlaFetcher,
        SSHFetcher
    )

__all__ = [
    "BaseDataFetcher",
    "BoundingBox",
    "TimeRange",
    "FetchResult",
    "SSTFetcher",
    "ChlaFetcher",
    "SSHFetcher",
]
