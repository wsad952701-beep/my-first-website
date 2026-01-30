"""
Open-Meteo API 基礎封裝

提供對 Open-Meteo 各端點的統一存取，包括：
- 天氣預報 API
- 海洋預報 API (波浪、涌浪、海流)
- 歷史數據 API
- 空氣品質 API

所有 API 均免費、無需 API Key。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import logging
import time

import requests
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class OpenMeteoEndpoint(Enum):
    """Open-Meteo API 端點"""
    FORECAST = "https://api.open-meteo.com/v1/forecast"
    GFS = "https://api.open-meteo.com/v1/gfs"
    ECMWF = "https://api.open-meteo.com/v1/ecmwf"
    JMA = "https://api.open-meteo.com/v1/jma"
    ICON = "https://api.open-meteo.com/v1/icon"
    GEM = "https://api.open-meteo.com/v1/gem"
    METEOFRANCE = "https://api.open-meteo.com/v1/meteofrance"
    UKMO = "https://api.open-meteo.com/v1/ukmo"
    MARINE = "https://marine-api.open-meteo.com/v1/marine"
    ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
    AIR_QUALITY = "https://air-quality-api.open-meteo.com/v1/air-quality"
    ENSEMBLE = "https://ensemble-api.open-meteo.com/v1/ensemble"


@dataclass
class WeatherVariables:
    """可用的氣象變量集合"""
    
    # 溫度相關
    TEMPERATURE: List[str] = field(default_factory=lambda: [
        "temperature_2m",
        "temperature_80m",
        "temperature_120m",
        "apparent_temperature",
    ])
    
    # 風相關
    WIND: List[str] = field(default_factory=lambda: [
        "wind_speed_10m",
        "wind_speed_80m",
        "wind_speed_120m",
        "wind_direction_10m",
        "wind_direction_80m",
        "wind_gusts_10m",
    ])
    
    # 氣壓
    PRESSURE: List[str] = field(default_factory=lambda: [
        "pressure_msl",
        "surface_pressure",
    ])
    
    # 降水
    PRECIPITATION: List[str] = field(default_factory=lambda: [
        "precipitation",
        "precipitation_probability",
        "rain",
        "showers",
        "snowfall",
    ])
    
    # 雲量與能見度
    CLOUD_VISIBILITY: List[str] = field(default_factory=lambda: [
        "cloud_cover",
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
        "visibility",
    ])
    
    # 濕度
    HUMIDITY: List[str] = field(default_factory=lambda: [
        "relative_humidity_2m",
        "dewpoint_2m",
    ])
    
    # 輻射
    RADIATION: List[str] = field(default_factory=lambda: [
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
    ])
    
    # 其他
    OTHER: List[str] = field(default_factory=lambda: [
        "cape",
        "weather_code",
        "is_day",
    ])


@dataclass
class MarineVariables:
    """海洋氣象變量"""
    
    # 綜合波浪
    WAVE: List[str] = field(default_factory=lambda: [
        "wave_height",
        "wave_direction",
        "wave_period",
    ])
    
    # 風浪
    WIND_WAVE: List[str] = field(default_factory=lambda: [
        "wind_wave_height",
        "wind_wave_direction",
        "wind_wave_period",
        "wind_wave_peak_period",
    ])
    
    # 涌浪
    SWELL: List[str] = field(default_factory=lambda: [
        "swell_wave_height",
        "swell_wave_direction",
        "swell_wave_period",
        "swell_wave_peak_period",
    ])
    
    # 海流
    CURRENT: List[str] = field(default_factory=lambda: [
        "ocean_current_velocity",
        "ocean_current_direction",
    ])


class OpenMeteoClient:
    """
    Open-Meteo API 客戶端
    
    提供對所有 Open-Meteo 端點的統一存取，
    包含自動重試、錯誤處理與數據解析。
    
    Attributes:
        timeout: 請求超時時間 (秒)
        max_retries: 最大重試次數
        retry_delay: 重試間隔 (秒)
    
    Example:
        >>> client = OpenMeteoClient()
        >>> df = client.get_forecast(25.0, 121.5, forecast_days=3)
        >>> print(df.head())
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 Open-Meteo 客戶端
        
        Args:
            timeout: 請求超時時間 (秒)
            max_retries: 最大重試次數
            retry_delay: 重試間隔基礎時間 (秒)，使用指數退避
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PFZ-System/1.0",
            "Accept": "application/json"
        })
    
    def _make_request(
        self,
        url: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        發送 HTTP 請求，帶自動重試
        
        Args:
            url: API 端點 URL
            params: 查詢參數
            
        Returns:
            JSON 響應數據
            
        Raises:
            requests.RequestException: 所有重試失敗後
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
        
        logger.error(f"All {self.max_retries} attempts failed for {url}")
        raise last_exception or requests.RequestException("Unknown error")
    
    def _parse_hourly_to_dataframe(
        self,
        data: Dict[str, Any],
        lat: float,
        lon: float
    ) -> pd.DataFrame:
        """
        將 API 響應的 hourly 數據轉換為 DataFrame
        
        Args:
            data: API 響應 JSON
            lat: 緯度
            lon: 經度
            
        Returns:
            包含時序數據的 DataFrame
        """
        hourly = data.get("hourly", {})
        if not hourly or "time" not in hourly:
            return pd.DataFrame()
        
        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        df["lat"] = lat
        df["lon"] = lon
        
        return df
    
    def get_forecast(
        self,
        lat: float,
        lon: float,
        variables: Optional[List[str]] = None,
        forecast_days: int = 7,
        endpoint: OpenMeteoEndpoint = OpenMeteoEndpoint.FORECAST,
        timezone: str = "UTC"
    ) -> pd.DataFrame:
        """
        獲取天氣預報
        
        Args:
            lat: 緯度 (-90 到 90)
            lon: 經度 (-180 到 180)
            variables: 要獲取的變量列表，None 則使用預設
            forecast_days: 預報天數 (1-16)
            endpoint: API 端點
            timezone: 時區
            
        Returns:
            包含預報數據的 DataFrame
            
        Example:
            >>> df = client.get_forecast(25.0, 121.5)
            >>> print(df.columns.tolist())
            ['time', 'temperature_2m', 'wind_speed_10m', ...]
        """
        if variables is None:
            variables = [
                "temperature_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "pressure_msl",
                "cloud_cover",
                "precipitation",
                "precipitation_probability",
                "visibility",
                "weather_code"
            ]
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "forecast_days": min(forecast_days, 16),
            "timezone": timezone
        }
        
        data = self._make_request(endpoint.value, params)
        return self._parse_hourly_to_dataframe(data, lat, lon)
    
    def get_marine_forecast(
        self,
        lat: float,
        lon: float,
        variables: Optional[List[str]] = None,
        forecast_days: int = 7,
        timezone: str = "UTC"
    ) -> pd.DataFrame:
        """
        獲取海洋氣象預報 (波浪、涌浪、海流)
        
        Args:
            lat: 緯度
            lon: 經度
            variables: 海洋變量列表
            forecast_days: 預報天數 (最多 7 天)
            timezone: 時區
            
        Returns:
            包含海洋預報數據的 DataFrame
        """
        marine_vars = MarineVariables()
        
        if variables is None:
            variables = (
                marine_vars.WAVE +
                marine_vars.WIND_WAVE +
                marine_vars.SWELL +
                marine_vars.CURRENT
            )
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "forecast_days": min(forecast_days, 7),
            "timezone": timezone
        }
        
        data = self._make_request(OpenMeteoEndpoint.MARINE.value, params)
        return self._parse_hourly_to_dataframe(data, lat, lon)
    
    def get_air_quality(
        self,
        lat: float,
        lon: float,
        forecast_days: int = 3,
        timezone: str = "UTC"
    ) -> pd.DataFrame:
        """
        獲取空氣品質預報
        
        Args:
            lat: 緯度
            lon: 經度
            forecast_days: 預報天數
            timezone: 時區
            
        Returns:
            包含空氣品質數據的 DataFrame
        """
        variables = [
            "pm2_5",
            "pm10",
            "us_aqi",
            "european_aqi",
            "dust",
            "uv_index"
        ]
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "forecast_days": min(forecast_days, 5),
            "timezone": timezone
        }
        
        data = self._make_request(OpenMeteoEndpoint.AIR_QUALITY.value, params)
        return self._parse_hourly_to_dataframe(data, lat, lon)
    
    def get_historical(
        self,
        lat: float,
        lon: float,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        variables: Optional[List[str]] = None,
        timezone: str = "UTC"
    ) -> pd.DataFrame:
        """
        獲取歷史天氣數據
        
        Args:
            lat: 緯度
            lon: 經度
            start_date: 開始日期 (YYYY-MM-DD 或 datetime)
            end_date: 結束日期
            variables: 變量列表
            timezone: 時區
            
        Returns:
            包含歷史數據的 DataFrame
        """
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")
        
        if variables is None:
            variables = [
                "temperature_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
                "pressure_msl"
            ]
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(variables),
            "timezone": timezone
        }
        
        data = self._make_request(OpenMeteoEndpoint.ARCHIVE.value, params)
        return self._parse_hourly_to_dataframe(data, lat, lon)
    
    def get_current_conditions(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        獲取當前天氣狀況
        
        Args:
            lat: 緯度
            lon: 經度
            
        Returns:
            當前天氣數據字典
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "pressure_msl"
            ]),
            "timezone": "UTC"
        }
        
        data = self._make_request(OpenMeteoEndpoint.FORECAST.value, params)
        current = data.get("current", {})
        current["lat"] = lat
        current["lon"] = lon
        
        return current


def decode_weather_code(code: int) -> Dict[str, str]:
    """
    解碼 WMO 天氣代碼
    
    Args:
        code: WMO 天氣代碼 (0-99)
        
    Returns:
        包含描述和圖標的字典
    """
    weather_codes = {
        0: {"description": "晴天", "icon": "☀️"},
        1: {"description": "晴時多雲", "icon": "🌤️"},
        2: {"description": "多雲", "icon": "⛅"},
        3: {"description": "陰天", "icon": "☁️"},
        45: {"description": "霧", "icon": "🌫️"},
        48: {"description": "霧凇", "icon": "🌫️"},
        51: {"description": "毛毛雨", "icon": "🌧️"},
        53: {"description": "中等毛毛雨", "icon": "🌧️"},
        55: {"description": "強毛毛雨", "icon": "🌧️"},
        56: {"description": "凍毛毛雨", "icon": "🌧️"},
        57: {"description": "強凍毛毛雨", "icon": "🌧️"},
        61: {"description": "小雨", "icon": "🌧️"},
        63: {"description": "中雨", "icon": "🌧️"},
        65: {"description": "大雨", "icon": "🌧️"},
        66: {"description": "凍雨", "icon": "🌧️"},
        67: {"description": "強凍雨", "icon": "🌧️"},
        71: {"description": "小雪", "icon": "❄️"},
        73: {"description": "中雪", "icon": "❄️"},
        75: {"description": "大雪", "icon": "❄️"},
        77: {"description": "霰", "icon": "❄️"},
        80: {"description": "小陣雨", "icon": "🌦️"},
        81: {"description": "中陣雨", "icon": "🌦️"},
        82: {"description": "大陣雨", "icon": "🌦️"},
        85: {"description": "小陣雪", "icon": "🌨️"},
        86: {"description": "大陣雪", "icon": "🌨️"},
        95: {"description": "雷雨", "icon": "⛈️"},
        96: {"description": "雷雨伴冰雹", "icon": "⛈️"},
        99: {"description": "強雷雨伴冰雹", "icon": "⛈️"},
    }
    
    return weather_codes.get(code, {"description": "未知", "icon": "❓"})


def wind_speed_to_beaufort(wind_ms: float) -> Dict[str, Any]:
    """
    將風速 (m/s) 轉換為蒲福風級
    
    Args:
        wind_ms: 風速 (m/s)
        
    Returns:
        包含風級、描述和影響的字典
    """
    beaufort_scale = [
        (0.3, 0, "無風", "煙直上"),
        (1.5, 1, "軟風", "煙微斜"),
        (3.3, 2, "輕風", "樹葉微動"),
        (5.4, 3, "微風", "旗展開"),
        (7.9, 4, "和風", "塵沙揚起"),
        (10.7, 5, "清風", "小樹搖擺"),
        (13.8, 6, "強風", "大樹搖擺"),
        (17.1, 7, "疾風", "全樹搖動"),
        (20.7, 8, "大風", "小樹枝折"),
        (24.4, 9, "烈風", "輕微損壞"),
        (28.4, 10, "狂風", "樹木拔起"),
        (32.6, 11, "暴風", "嚴重損壞"),
        (float("inf"), 12, "颱風", "摧毀性")
    ]
    
    for threshold, scale, name, effect in beaufort_scale:
        if wind_ms < threshold:
            return {
                "scale": scale,
                "name": name,
                "effect": effect,
                "wind_ms": wind_ms
            }
    
    return {"scale": 12, "name": "颱風", "effect": "摧毀性", "wind_ms": wind_ms}
