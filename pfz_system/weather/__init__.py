"""
PFZ Weather Module - 氣象數據整合

提供多來源氣象數據獲取、海洋預報、颱風監測與作業適宜度評估。

Modules:
    - openmeteo: Open-Meteo API 基礎封裝
    - global_models: 多國氣象模型整合
    - operability: 漁業作業適宜度評估
    - typhoon: 颱風/熱帶氣旋監測
"""

try:
    from .openmeteo import OpenMeteoClient
    from .global_models import GlobalWeatherFetcher, WeatherModel, get_weather_forecast
    from .operability import OperabilityCalculator, VesselType, get_operability_forecast
    from .typhoon import TyphoonMonitor, TyphoonInfo
except ImportError:
    from openmeteo import OpenMeteoClient
    from global_models import GlobalWeatherFetcher, WeatherModel, get_weather_forecast
    from operability import OperabilityCalculator, VesselType, get_operability_forecast
    from typhoon import TyphoonMonitor, TyphoonInfo

__all__ = [
    "OpenMeteoClient",
    "GlobalWeatherFetcher",
    "WeatherModel",
    "get_weather_forecast",
    "OperabilityCalculator",
    "VesselType",
    "get_operability_forecast",
    "TyphoonMonitor",
    "TyphoonInfo",
]
