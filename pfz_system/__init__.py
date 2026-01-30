"""
PFZ System - 潛在漁場預測系統

整合海洋環境數據與氣象預報，提供精準漁場預測。

Modules:
    - config: 系統配置
    - data: 數據獲取
    - weather: 氣象預報
    - algorithms: 預測算法
    - business: 商業分析
    - notification: 通知服務
"""

__version__ = "1.0.0"
__author__ = "PFZ Development Team"

try:
    from .config import get_settings, configure_logging
    from .algorithms import PFZCalculator, calculate_pfz, PFZPrediction
    from .weather import get_weather_forecast, get_operability_forecast
except ImportError:
    from config import get_settings, configure_logging
    from algorithms import PFZCalculator, calculate_pfz, PFZPrediction
    from weather import get_weather_forecast, get_operability_forecast

__all__ = [
    # Version
    "__version__",
    # Config
    "get_settings",
    "configure_logging",
    # Core
    "PFZCalculator",
    "calculate_pfz",
    "PFZPrediction",
    # Weather
    "get_weather_forecast",
    "get_operability_forecast",
]
