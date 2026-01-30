"""
Pytest 配置與共用 Fixtures

提供測試所需的 mock 數據和共用設定。
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# Mock 數據 Fixtures
# ============================================

@pytest.fixture
def sample_coordinates():
    """標準測試座標 - 台灣東部海域"""
    return {
        "lat": 22.5,
        "lon": 121.0
    }


@pytest.fixture
def sample_coordinates_list():
    """多個測試座標"""
    return [
        {"lat": 22.5, "lon": 121.0, "name": "台灣東部"},
        {"lat": 24.0, "lon": 122.0, "name": "蘭嶼外海"},
        {"lat": 25.0, "lon": 123.0, "name": "琉球海域"},
    ]


@pytest.fixture
def mock_sst_data():
    """模擬 SST 數據"""
    return {
        "value": 26.5,
        "unit": "°C",
        "time": datetime.now().isoformat(),
        "source": "mock"
    }


@pytest.fixture
def mock_chla_data():
    """模擬葉綠素 a 數據"""
    return {
        "value": 0.35,
        "unit": "mg/m³",
        "time": datetime.now().isoformat(),
        "source": "mock"
    }


@pytest.fixture
def mock_weather_data():
    """模擬氣象預報數據"""
    base_time = datetime.now()
    return {
        "forecast": [
            {
                "time": (base_time + timedelta(hours=i*6)).isoformat(),
                "temperature": 28.0 + (i * 0.5),
                "wind_speed": 15.0 + (i * 2),
                "wind_direction": 45 + (i * 10),
                "wave_height": 1.5 + (i * 0.2),
                "precipitation": 0.0
            }
            for i in range(12)
        ],
        "model": "GFS",
        "updated": base_time.isoformat()
    }


@pytest.fixture
def mock_pfz_score():
    """模擬 PFZ 分數"""
    return {
        "total_score": 75.0,
        "habitat_score": 80.0,
        "front_score": 70.0,
        "eddy_score": 65.0,
        "weather_score": 85.0,
        "trend_score": 75.0,
        "confidence": 0.72,
        "recommendation": "✅ 良好漁場，建議出航作業"
    }


@pytest.fixture
def sample_vessel_specs():
    """標準延繩釣漁船規格"""
    return {
        "name": "測試漁船",
        "length_m": 45.0,
        "tonnage_gt": 200,
        "engine_hp": 800,
        "fuel_consumption_l_per_nm": 2.5,
        "crew_size": 12,
        "operating_cost_per_day": 500
    }


@pytest.fixture
def sample_roi_input():
    """ROI 計算輸入"""
    return {
        "origin": (22.6, 120.3),
        "destination": (24.0, 122.0),
        "pfz_score": 75,
        "target_species": "yellowfin_tuna",
        "operation_days": 5
    }


# ============================================
# Mock 服務 Fixtures
# ============================================

@pytest.fixture
def mock_sst_fetcher():
    """模擬 SST 數據獲取器"""
    with patch("data.fetchers.sst.SSTFetcher") as mock:
        instance = MagicMock()
        instance.get_sst.return_value = 26.5
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_chla_fetcher():
    """模擬 Chl-a 數據獲取器"""
    with patch("data.fetchers.chla.ChlaFetcher") as mock:
        instance = MagicMock()
        instance.get_chla.return_value = 0.35
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_weather_fetcher():
    """模擬氣象獲取器"""
    with patch("weather.openmeteo.OpenMeteoClient") as mock:
        instance = MagicMock()
        instance.get_forecast.return_value = {
            "temperature": [28.0] * 24,
            "wind_speed": [15.0] * 24,
            "wave_height": [1.5] * 24
        }
        mock.return_value = instance
        yield instance


# ============================================
# 環境配置 Fixtures
# ============================================

@pytest.fixture(autouse=True)
def setup_test_env():
    """自動設置測試環境"""
    # 設置測試環境變數
    os.environ.setdefault("PFZ_ENV", "test")
    os.environ.setdefault("PFZ_CACHE_ENABLED", "false")
    yield
    # 清理


@pytest.fixture
def temp_cache_dir(tmp_path):
    """臨時快取目錄"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


# ============================================
# 輔助函數
# ============================================

def assert_score_in_range(score: float, min_val: float = 0, max_val: float = 100):
    """驗證分數在有效範圍內"""
    assert min_val <= score <= max_val, f"Score {score} not in range [{min_val}, {max_val}]"


def assert_coordinates_valid(lat: float, lon: float):
    """驗證座標有效"""
    assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
    assert -180 <= lon <= 180, f"Invalid longitude: {lon}"
