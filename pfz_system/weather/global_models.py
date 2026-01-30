"""
全球氣象模型整合

支持多個國家氣象局的預報模型，提供：
- 智能模型選擇（根據地理位置）
- 多模型並行獲取
- 集成預報（Ensemble）計算
- 不確定性評估

支持的模型:
- NOAA GFS (美國) - 全球 28km 16天
- ECMWF IFS (歐洲) - 全球 9km 15天
- JMA GSM (日本) - 全球 20km 11天
- DWD ICON (德國) - 全球 13km 7.5天
- GEM (加拿大) - 全球 25km 10天
- Météo-France ARPEGE - 全球 10km 4天
- UK Met Office - 全球 10km 7天
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

import pandas as pd
import numpy as np

from .openmeteo import OpenMeteoClient, OpenMeteoEndpoint

logger = logging.getLogger(__name__)


class WeatherModel(Enum):
    """支持的氣象模型枚舉"""
    AUTO = "forecast"           # 自動選擇最佳
    GFS = "gfs"                 # NOAA GFS (美國)
    ECMWF = "ecmwf"             # ECMWF IFS (歐洲)
    JMA = "jma"                 # JMA GSM (日本)
    ICON = "icon"               # DWD ICON (德國)
    GEM = "gem"                 # Environment Canada
    METEOFRANCE = "meteofrance" # Météo-France
    UKMO = "ukmo"               # UK Met Office


@dataclass
class ModelSpec:
    """氣象模型規格定義"""
    name: str
    provider: str
    country: str
    country_flag: str
    resolution_km: float
    forecast_days: int
    update_hours: List[int]
    best_regions: List[str]
    api_endpoint: str
    
    def __str__(self) -> str:
        return f"{self.country_flag} {self.name} ({self.provider})"


# 模型規格定義
MODEL_SPECS: Dict[WeatherModel, ModelSpec] = {
    WeatherModel.GFS: ModelSpec(
        name="Global Forecast System",
        provider="NOAA/NCEP",
        country="美國",
        country_flag="🇺🇸",
        resolution_km=28,
        forecast_days=16,
        update_hours=[0, 6, 12, 18],
        best_regions=["全球", "北美", "東太平洋", "墨西哥灣"],
        api_endpoint="https://api.open-meteo.com/v1/gfs"
    ),
    WeatherModel.ECMWF: ModelSpec(
        name="ECMWF IFS",
        provider="ECMWF",
        country="歐洲",
        country_flag="🇪🇺",
        resolution_km=9,
        forecast_days=15,
        update_hours=[0, 6, 12, 18],
        best_regions=["全球", "歐洲", "大西洋", "印度洋", "地中海"],
        api_endpoint="https://api.open-meteo.com/v1/ecmwf"
    ),
    WeatherModel.JMA: ModelSpec(
        name="JMA GSM",
        provider="JMA",
        country="日本",
        country_flag="🇯🇵",
        resolution_km=20,
        forecast_days=11,
        update_hours=[0, 6, 12, 18],
        best_regions=["西太平洋", "亞太", "日本近海", "南海", "台灣"],
        api_endpoint="https://api.open-meteo.com/v1/jma"
    ),
    WeatherModel.ICON: ModelSpec(
        name="DWD ICON",
        provider="DWD",
        country="德國",
        country_flag="🇩🇪",
        resolution_km=13,
        forecast_days=7,
        update_hours=[0, 6, 12, 18],
        best_regions=["全球", "歐洲", "大西洋", "北海"],
        api_endpoint="https://api.open-meteo.com/v1/icon"
    ),
    WeatherModel.GEM: ModelSpec(
        name="GEM",
        provider="Environment Canada",
        country="加拿大",
        country_flag="🇨🇦",
        resolution_km=25,
        forecast_days=10,
        update_hours=[0, 12],
        best_regions=["北美", "北大西洋", "北極", "太平洋東北"],
        api_endpoint="https://api.open-meteo.com/v1/gem"
    ),
    WeatherModel.METEOFRANCE: ModelSpec(
        name="ARPEGE",
        provider="Météo-France",
        country="法國",
        country_flag="🇫🇷",
        resolution_km=10,
        forecast_days=4,
        update_hours=[0, 6, 12, 18],
        best_regions=["歐洲", "地中海", "大西洋", "非洲西北"],
        api_endpoint="https://api.open-meteo.com/v1/meteofrance"
    ),
    WeatherModel.UKMO: ModelSpec(
        name="UK Met Office",
        provider="Met Office",
        country="英國",
        country_flag="🇬🇧",
        resolution_km=10,
        forecast_days=7,
        update_hours=[0, 6, 12, 18],
        best_regions=["歐洲", "北大西洋", "英倫三島", "北海"],
        api_endpoint="https://api.open-meteo.com/v1/ukmo"
    ),
}


@dataclass
class RegionBounds:
    """地理區域邊界"""
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    preferred_models: List[WeatherModel]


# 區域定義與推薦模型
REGION_DEFINITIONS: List[RegionBounds] = [
    RegionBounds(
        name="西太平洋",
        lat_min=-10, lat_max=50,
        lon_min=100, lon_max=180,
        preferred_models=[WeatherModel.JMA, WeatherModel.ECMWF, WeatherModel.GFS]
    ),
    RegionBounds(
        name="印度洋",
        lat_min=-30, lat_max=20,
        lon_min=40, lon_max=100,
        preferred_models=[WeatherModel.ECMWF, WeatherModel.GFS]
    ),
    RegionBounds(
        name="北美",
        lat_min=20, lat_max=70,
        lon_min=-170, lon_max=-50,
        preferred_models=[WeatherModel.GFS, WeatherModel.GEM]
    ),
    RegionBounds(
        name="歐洲/大西洋",
        lat_min=30, lat_max=70,
        lon_min=-30, lon_max=40,
        preferred_models=[WeatherModel.ECMWF, WeatherModel.ICON, WeatherModel.UKMO]
    ),
    RegionBounds(
        name="南半球",
        lat_min=-60, lat_max=-10,
        lon_min=-180, lon_max=180,
        preferred_models=[WeatherModel.ECMWF, WeatherModel.GFS]
    ),
]


class GlobalWeatherFetcher:
    """
    全球氣象數據獲取器
    
    支持多模型並行獲取和智能選擇，提供集成預報計算。
    
    Attributes:
        timeout: 請求超時時間
        max_workers: 並行工作線程數
        client: Open-Meteo 客戶端實例
    
    Example:
        >>> fetcher = GlobalWeatherFetcher()
        >>> models = fetcher.select_best_models(25.0, 121.5)
        >>> print([m.value for m in models])
        ['jma', 'ecmwf', 'gfs']
        
        >>> ensemble = fetcher.fetch_ensemble(25.0, 121.5, forecast_days=3)
        >>> print(ensemble.columns.tolist())
    """
    
    MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
    
    DEFAULT_VARIABLES = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "pressure_msl",
        "cloud_cover",
        "precipitation",
        "visibility"
    ]
    
    def __init__(
        self,
        timeout: int = 30,
        max_workers: int = 5,
        max_retries: int = 3
    ):
        """
        初始化全球氣象獲取器
        
        Args:
            timeout: 請求超時時間 (秒)
            max_workers: 並行工作線程數
            max_retries: 最大重試次數
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.client = OpenMeteoClient(
            timeout=timeout,
            max_retries=max_retries
        )
    
    def select_best_models(
        self,
        lat: float,
        lon: float,
        forecast_hours: int = 72
    ) -> List[WeatherModel]:
        """
        根據位置和預報時長智能選擇最佳模型組合
        
        選擇策略：
        1. 根據地理位置匹配最佳區域
        2. 使用該區域的推薦模型
        3. 長期預報 (>7天) 自動加入 GFS
        
        Args:
            lat: 緯度 (-90 到 90)
            lon: 經度 (-180 到 180)
            forecast_hours: 預報時長 (小時)
            
        Returns:
            推薦的模型列表
        """
        # 查找匹配的區域
        for region in REGION_DEFINITIONS:
            if (region.lat_min <= lat <= region.lat_max and
                region.lon_min <= lon <= region.lon_max):
                models = list(region.preferred_models)
                break
        else:
            # 默認使用全球模型
            models = [WeatherModel.ECMWF, WeatherModel.GFS]
        
        # 長期預報確保有 GFS (16天預報)
        if forecast_hours > 168 and WeatherModel.GFS not in models:
            models.append(WeatherModel.GFS)
        
        return models
    
    def get_model_info(self, model: WeatherModel) -> Optional[ModelSpec]:
        """
        獲取模型規格資訊
        
        Args:
            model: 模型枚舉
            
        Returns:
            模型規格，若不存在則返回 None
        """
        return MODEL_SPECS.get(model)
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        列出所有可用模型及其規格
        
        Returns:
            模型資訊列表
        """
        return [
            {
                "id": model.value,
                "name": spec.name,
                "provider": spec.provider,
                "country": spec.country,
                "flag": spec.country_flag,
                "resolution_km": spec.resolution_km,
                "forecast_days": spec.forecast_days,
                "best_regions": spec.best_regions
            }
            for model, spec in MODEL_SPECS.items()
        ]
    
    def fetch_single_model(
        self,
        lat: float,
        lon: float,
        model: WeatherModel,
        forecast_days: int = 7,
        variables: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        獲取單一模型的預報數據
        
        Args:
            lat: 緯度
            lon: 經度
            model: 目標模型
            forecast_days: 預報天數
            variables: 變量列表
            
        Returns:
            預報數據 DataFrame，失敗則返回 None
        """
        spec = MODEL_SPECS.get(model)
        if spec is None:
            logger.warning(f"Unknown model: {model}")
            return None
        
        # 限制預報天數不超過模型上限
        days = min(forecast_days, spec.forecast_days)
        
        if variables is None:
            variables = self.DEFAULT_VARIABLES
        
        # Map WeatherModel to OpenMeteoEndpoint
        model_to_endpoint = {
            WeatherModel.AUTO: OpenMeteoEndpoint.FORECAST,
            WeatherModel.GFS: OpenMeteoEndpoint.GFS,
            WeatherModel.ECMWF: OpenMeteoEndpoint.ECMWF,
            WeatherModel.JMA: OpenMeteoEndpoint.JMA,
            WeatherModel.ICON: OpenMeteoEndpoint.ICON,
            WeatherModel.GEM: OpenMeteoEndpoint.GEM,
            WeatherModel.METEOFRANCE: OpenMeteoEndpoint.METEOFRANCE,
            WeatherModel.UKMO: OpenMeteoEndpoint.UKMO,
        }
        
        try:
            endpoint = model_to_endpoint.get(model, OpenMeteoEndpoint.FORECAST)
            df = self.client.get_forecast(
                lat, lon,
                variables=variables,
                forecast_days=days,
                endpoint=endpoint
            )
            
            if not df.empty:
                df["model"] = model.value
                df["model_name"] = spec.name
            
            return df
            
        except Exception as e:
            logger.warning(f"Failed to fetch {model.value}: {e}")
            return None
    
    def fetch_multi_model(
        self,
        lat: float,
        lon: float,
        models: Optional[List[WeatherModel]] = None,
        forecast_days: int = 7,
        variables: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        並行獲取多個模型的預報
        
        Args:
            lat: 緯度
            lon: 經度
            models: 模型列表，None 則自動選擇
            forecast_days: 預報天數
            variables: 變量列表
            
        Returns:
            字典 {model_name: DataFrame}
        """
        if models is None:
            models = self.select_best_models(lat, lon, forecast_days * 24)
        
        if variables is None:
            variables = self.DEFAULT_VARIABLES
        
        results: Dict[str, pd.DataFrame] = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_model = {
                executor.submit(
                    self.fetch_single_model,
                    lat, lon, model, forecast_days, variables
                ): model
                for model in models
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results[model.value] = df
                        logger.debug(f"Successfully fetched {model.value}")
                except Exception as e:
                    logger.warning(f"Model {model.value} failed: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(models)} models for ({lat}, {lon})")
        return results
    
    def fetch_marine(
        self,
        lat: float,
        lon: float,
        forecast_days: int = 7
    ) -> Optional[pd.DataFrame]:
        """
        獲取海洋氣象預報 (波浪、涌浪、海流)
        
        Args:
            lat: 緯度
            lon: 經度
            forecast_days: 預報天數 (最多 7 天)
            
        Returns:
            海洋預報 DataFrame
        """
        try:
            return self.client.get_marine_forecast(
                lat, lon,
                forecast_days=min(forecast_days, 7)
            )
        except Exception as e:
            logger.warning(f"Marine forecast failed: {e}")
            return None
    
    def fetch_ensemble(
        self,
        lat: float,
        lon: float,
        forecast_days: int = 7,
        include_marine: bool = True
    ) -> pd.DataFrame:
        """
        獲取多模型集成預報
        
        計算多模型的平均值、標準差、最小/最大值，
        提供預報不確定性評估。
        
        Args:
            lat: 緯度
            lon: 經度
            forecast_days: 預報天數
            include_marine: 是否包含海洋數據
            
        Returns:
            集成預報 DataFrame，包含統計列
        """
        # 選擇最佳模型
        models = self.select_best_models(lat, lon, forecast_days * 24)
        
        # 並行獲取數據
        multi_data = self.fetch_multi_model(lat, lon, models, forecast_days)
        
        if not multi_data:
            logger.error(f"No model data available for ({lat}, {lon})")
            return pd.DataFrame()
        
        # 合併所有模型數據
        all_dfs = list(multi_data.values())
        combined = pd.concat(all_dfs, ignore_index=True)
        
        # 定義需要計算統計的數值列
        numeric_cols = [
            "wind_speed_10m",
            "wind_gusts_10m",
            "temperature_2m",
            "pressure_msl",
            "cloud_cover",
            "precipitation",
            "visibility"
        ]
        available_cols = [c for c in numeric_cols if c in combined.columns]
        
        if not available_cols:
            logger.warning("No numeric columns found for ensemble calculation")
            return combined
        
        # 按時間分組計算統計量
        ensemble = combined.groupby("time")[available_cols].agg(
            ["mean", "std", "min", "max"]
        )
        
        # 扁平化多級列名
        ensemble.columns = [f"{col}_{stat}" for col, stat in ensemble.columns]
        ensemble = ensemble.reset_index()
        
        # 添加元數據
        ensemble["lat"] = lat
        ensemble["lon"] = lon
        ensemble["n_models"] = len(multi_data)
        ensemble["models_used"] = ",".join(multi_data.keys())
        
        # 可選加入海洋數據
        if include_marine:
            marine = self.fetch_marine(lat, lon, forecast_days)
            if marine is not None and not marine.empty:
                marine_cols = [
                    "wave_height", "wave_direction", "wave_period",
                    "swell_wave_height", "ocean_current_velocity"
                ]
                available_marine = [c for c in marine_cols if c in marine.columns]
                if available_marine:
                    ensemble = ensemble.merge(
                        marine[["time"] + available_marine],
                        on="time",
                        how="left"
                    )
        
        return ensemble


def get_weather_forecast(
    lat: float,
    lon: float,
    days: int = 3,
    include_marine: bool = True
) -> pd.DataFrame:
    """
    便捷函數：獲取氣象預報
    
    自動選擇最佳模型，返回集成預報。
    
    Args:
        lat: 緯度
        lon: 經度
        days: 預報天數
        include_marine: 是否包含海洋數據
        
    Returns:
        集成預報 DataFrame
        
    Example:
        >>> forecast = get_weather_forecast(25.0, 121.5, days=3)
        >>> print(forecast[['time', 'wind_speed_10m_mean', 'wave_height']].head())
    """
    fetcher = GlobalWeatherFetcher()
    return fetcher.fetch_ensemble(lat, lon, days, include_marine)


def compare_models_at_point(
    lat: float,
    lon: float,
    days: int = 3
) -> pd.DataFrame:
    """
    比較不同模型在同一位置的預報差異
    
    Args:
        lat: 緯度
        lon: 經度
        days: 預報天數
        
    Returns:
        包含所有模型預報的 DataFrame
    """
    fetcher = GlobalWeatherFetcher()
    
    all_models = [
        WeatherModel.GFS,
        WeatherModel.ECMWF,
        WeatherModel.JMA,
        WeatherModel.ICON
    ]
    
    results = fetcher.fetch_multi_model(lat, lon, all_models, days)
    
    if results:
        return pd.concat(results.values(), ignore_index=True)
    return pd.DataFrame()


def get_model_recommendation(lat: float, lon: float) -> Dict[str, Any]:
    """
    獲取位置的模型推薦報告
    
    Args:
        lat: 緯度
        lon: 經度
        
    Returns:
        包含推薦模型和原因的字典
    """
    fetcher = GlobalWeatherFetcher()
    models = fetcher.select_best_models(lat, lon)
    
    recommendations = []
    for model in models:
        spec = MODEL_SPECS.get(model)
        if spec:
            recommendations.append({
                "model": model.value,
                "name": str(spec),
                "resolution_km": spec.resolution_km,
                "forecast_days": spec.forecast_days,
                "best_regions": spec.best_regions
            })
    
    return {
        "location": {"lat": lat, "lon": lon},
        "recommended_models": recommendations,
        "primary_model": models[0].value if models else None
    }
