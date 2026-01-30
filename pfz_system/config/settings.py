"""
PFZ System Configuration

系統全局配置，包括：
- API 端點設定
- 數據源配置
- 算法參數
- 通知設定
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

# 嘗試載入 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Environment(Enum):
    """運行環境"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class APIConfig:
    """API 配置"""
    # Open-Meteo (免費，無需 API Key)
    open_meteo_base: str = "https://api.open-meteo.com/v1"
    open_meteo_marine: str = "https://marine-api.open-meteo.com/v1/marine"
    open_meteo_archive: str = "https://archive-api.open-meteo.com/v1/archive"
    open_meteo_air_quality: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    # ERDDAP (海洋衛星數據)
    erddap_coastwatch: str = "https://coastwatch.pfeg.noaa.gov/erddap"
    erddap_copernicus: str = "https://my.cmems-du.eu/erddap"
    
    # 台灣中央氣象署 (需申請 API Key)
    cwa_base: str = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
    cwa_api_key: str = field(default_factory=lambda: os.getenv("CWA_API_KEY", ""))
    
    # Line Messaging API
    line_api_base: str = "https://api.line.me/v2/bot"
    line_channel_token: str = field(default_factory=lambda: os.getenv("LINE_CHANNEL_TOKEN", ""))
    line_channel_secret: str = field(default_factory=lambda: os.getenv("LINE_CHANNEL_SECRET", ""))
    line_user_id: str = field(default_factory=lambda: os.getenv("LINE_USER_ID", ""))


@dataclass
class DataConfig:
    """數據配置"""
    # SST 設定
    sst_dataset: str = "jplMURSST41"
    sst_variables: List[str] = field(default_factory=lambda: ["analysed_sst"])
    sst_resolution_km: float = 1.0
    
    # Chlorophyll-a 設定
    chla_dataset: str = "erdMH1chla8day"
    chla_variables: List[str] = field(default_factory=lambda: ["chlorophyll"])
    chla_resolution_km: float = 4.0
    
    # SSH 設定
    ssh_dataset: str = "nesdisSSH1day"
    ssh_variables: List[str] = field(default_factory=lambda: ["sea_surface_height"])
    
    # 緩存設定
    cache_enabled: bool = True
    cache_ttl_hours: int = 6
    cache_dir: Path = field(default_factory=lambda: Path("./cache"))


@dataclass
class AlgorithmConfig:
    """算法配置"""
    # PFZ 權重
    pfz_weights: Dict[str, float] = field(default_factory=lambda: {
        "habitat": 0.30,      # 棲息地指數
        "front": 0.20,        # 熱鋒面
        "eddy": 0.15,         # 渦旋
        "gradient": 0.10,     # 溫度梯度
        "weather": 0.15,      # 氣象適宜度
        "trend": 0.10         # 趨勢持續性
    })
    
    # 氣象適宜度權重
    weather_weights: Dict[str, float] = field(default_factory=lambda: {
        "wind": 0.40,
        "wave": 0.35,
        "visibility": 0.15,
        "precipitation": 0.10
    })
    
    # 鋒面檢測參數
    front_gradient_threshold: float = 0.5  # °C/km
    front_min_length_km: float = 10.0
    
    # 渦旋檢測參數
    eddy_min_radius_km: float = 50.0
    eddy_ssh_threshold_cm: float = 5.0
    
    # 熱點檢測參數
    hotspot_sst_range: tuple = (24.0, 30.0)  # °C
    hotspot_chla_min: float = 0.1  # mg/m³


@dataclass
class NotificationConfig:
    """通知配置"""
    # Line 設定
    line_enabled: bool = True
    line_default_recipients: List[str] = field(default_factory=list)
    
    # 通知觸發條件
    alert_pfz_score_threshold: float = 70.0
    alert_typhoon_radius_nm: float = 300.0
    alert_weather_change_threshold: float = 20.0  # 分數變化
    
    # 定時報告
    daily_report_enabled: bool = True
    daily_report_hour: int = 6  # 早上 6 點
    daily_report_timezone: str = "Asia/Taipei"


@dataclass
class Settings:
    """
    主設定類
    
    集中管理所有系統配置，支持環境變數覆蓋。
    
    Example:
        >>> settings = Settings()
        >>> print(settings.api.open_meteo_base)
        >>> print(settings.algorithm.pfz_weights)
    """
    environment: Environment = field(
        default_factory=lambda: Environment(os.getenv("PFZ_ENV", "development"))
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("PFZ_DEBUG", "false").lower() == "true"
    )
    
    api: APIConfig = field(default_factory=APIConfig)
    data: DataConfig = field(default_factory=DataConfig)
    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    
    # 日誌設定
    log_level: str = field(
        default_factory=lambda: os.getenv("PFZ_LOG_LEVEL", "INFO")
    )
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """初始化後處理"""
        # 確保緩存目錄存在
        if self.data.cache_enabled:
            self.data.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（不含敏感資訊）"""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "log_level": self.log_level,
            "api": {
                "open_meteo_base": self.api.open_meteo_base,
                "line_configured": bool(self.api.line_channel_token)
            },
            "algorithm": {
                "pfz_weights": self.algorithm.pfz_weights,
                "weather_weights": self.algorithm.weather_weights
            }
        }


# 全局設定實例
settings = Settings()


def get_settings() -> Settings:
    """獲取設定實例"""
    return settings


def configure_logging() -> None:
    """配置日誌系統"""
    import logging
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format
    )
    
    # 設定第三方庫日誌級別
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
