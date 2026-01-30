"""
漁場區域定義

定義各海域的地理邊界、特性與推薦配置，包括：
- 台灣周邊海域
- 西太平洋主要漁場
- 印度洋漁場
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class OceanBasin(Enum):
    """海洋盆地"""
    WESTERN_PACIFIC = "WPAC"      # 西太平洋
    CENTRAL_PACIFIC = "CPAC"      # 中太平洋
    EASTERN_PACIFIC = "EPAC"      # 東太平洋
    INDIAN_OCEAN = "IO"           # 印度洋
    ATLANTIC = "ATL"              # 大西洋
    SOUTH_CHINA_SEA = "SCS"       # 南海


@dataclass
class RegionBounds:
    """區域邊界定義"""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    
    def contains(self, lat: float, lon: float) -> bool:
        """檢查點是否在區域內"""
        return (self.lat_min <= lat <= self.lat_max and
                self.lon_min <= lon <= self.lon_max)
    
    def center(self) -> Tuple[float, float]:
        """獲取區域中心"""
        return (
            (self.lat_min + self.lat_max) / 2,
            (self.lon_min + self.lon_max) / 2
        )
    
    def area_km2(self) -> float:
        """估算面積 (平方公里)"""
        import math
        lat_center = (self.lat_min + self.lat_max) / 2
        lat_dist = 111.0 * (self.lat_max - self.lat_min)
        lon_dist = 111.0 * math.cos(math.radians(lat_center)) * (self.lon_max - self.lon_min)
        return lat_dist * lon_dist


@dataclass
class FishingRegion:
    """
    漁場區域定義
    
    Attributes:
        id: 區域識別碼
        name: 區域名稱
        name_en: 英文名稱
        basin: 所屬海洋盆地
        bounds: 地理邊界
        primary_species: 主要魚種
        best_seasons: 最佳季節 (月份)
        typical_sst_range: 典型海表溫度範圍 (°C)
        notes: 備註
    """
    id: str
    name: str
    name_en: str
    basin: OceanBasin
    bounds: RegionBounds
    primary_species: List[str] = field(default_factory=list)
    best_seasons: List[int] = field(default_factory=list)
    typical_sst_range: Tuple[float, float] = (20.0, 30.0)
    notes: str = ""
    
    def is_in_season(self, month: int) -> bool:
        """檢查是否為最佳季節"""
        return month in self.best_seasons if self.best_seasons else True


# ============================================
# 預定義漁場區域
# ============================================

FISHING_REGIONS: Dict[str, FishingRegion] = {
    # 台灣周邊
    "taiwan_east": FishingRegion(
        id="taiwan_east",
        name="台灣東部海域",
        name_en="Taiwan East Coast",
        basin=OceanBasin.WESTERN_PACIFIC,
        bounds=RegionBounds(
            lat_min=22.0, lat_max=25.5,
            lon_min=121.0, lon_max=124.0
        ),
        primary_species=["黑鮪", "旗魚", "鬼頭刀", "飛魚"],
        best_seasons=[4, 5, 6, 7, 8, 9],
        typical_sst_range=(24.0, 29.0),
        notes="黑潮流經，適合延繩釣與鏢旗魚"
    ),
    
    "taiwan_north": FishingRegion(
        id="taiwan_north",
        name="台灣北部海域",
        name_en="Taiwan North Coast",
        basin=OceanBasin.WESTERN_PACIFIC,
        bounds=RegionBounds(
            lat_min=25.0, lat_max=27.0,
            lon_min=120.0, lon_max=123.0
        ),
        primary_species=["白帶魚", "鯖魚", "竹筴魚", "透抽"],
        best_seasons=[9, 10, 11, 12, 1, 2],
        typical_sst_range=(18.0, 26.0),
        notes="秋冬季節性洄游魚群豐富"
    ),
    
    "taiwan_south": FishingRegion(
        id="taiwan_south",
        name="台灣南部海域",
        name_en="Taiwan South Coast",
        basin=OceanBasin.SOUTH_CHINA_SEA,
        bounds=RegionBounds(
            lat_min=20.0, lat_max=22.5,
            lon_min=118.0, lon_max=121.0
        ),
        primary_species=["黑鮪", "黃鰭鮪", "正鰹", "鬼頭刀"],
        best_seasons=[4, 5, 6, 7],
        typical_sst_range=(25.0, 30.0),
        notes="巴士海峽，黑鮪洄游路徑"
    ),
    
    "taiwan_west": FishingRegion(
        id="taiwan_west",
        name="台灣海峽",
        name_en="Taiwan Strait",
        basin=OceanBasin.SOUTH_CHINA_SEA,
        bounds=RegionBounds(
            lat_min=22.0, lat_max=26.0,
            lon_min=117.0, lon_max=120.5
        ),
        primary_species=["烏魚", "白帶魚", "鯖魚", "蝦蟹"],
        best_seasons=[10, 11, 12, 1, 2, 3],
        typical_sst_range=(16.0, 28.0),
        notes="淺海漁場，適合拖網與刺網"
    ),
    
    # 西太平洋遠洋
    "wpac_subtropical": FishingRegion(
        id="wpac_subtropical",
        name="西太平洋亞熱帶漁場",
        name_en="WPAC Subtropical",
        basin=OceanBasin.WESTERN_PACIFIC,
        bounds=RegionBounds(
            lat_min=20.0, lat_max=35.0,
            lon_min=120.0, lon_max=150.0
        ),
        primary_species=["長鰭鮪", "大目鮪", "黃鰭鮪", "旗魚"],
        best_seasons=[3, 4, 5, 9, 10, 11],
        typical_sst_range=(22.0, 28.0),
        notes="主要延繩釣漁場"
    ),
    
    "wpac_tropical": FishingRegion(
        id="wpac_tropical",
        name="西太平洋熱帶漁場",
        name_en="WPAC Tropical",
        basin=OceanBasin.WESTERN_PACIFIC,
        bounds=RegionBounds(
            lat_min=0.0, lat_max=20.0,
            lon_min=120.0, lon_max=170.0
        ),
        primary_species=["正鰹", "黃鰭鮪", "大目鮪", "長鰭鮪"],
        best_seasons=list(range(1, 13)),  # 全年
        typical_sst_range=(27.0, 31.0),
        notes="全年可作業，圍網與延繩釣"
    ),
    
    # 中西太平洋
    "cpfc_equatorial": FishingRegion(
        id="cpfc_equatorial",
        name="中西太平洋赤道漁場",
        name_en="WCPO Equatorial",
        basin=OceanBasin.CENTRAL_PACIFIC,
        bounds=RegionBounds(
            lat_min=-10.0, lat_max=10.0,
            lon_min=140.0, lon_max=180.0
        ),
        primary_species=["正鰹", "黃鰭鮪"],
        best_seasons=list(range(1, 13)),
        typical_sst_range=(28.0, 30.0),
        notes="全球最大鮪魚漁場之一"
    ),
    
    # 印度洋
    "io_western": FishingRegion(
        id="io_western",
        name="印度洋西部漁場",
        name_en="Western Indian Ocean",
        basin=OceanBasin.INDIAN_OCEAN,
        bounds=RegionBounds(
            lat_min=-20.0, lat_max=10.0,
            lon_min=40.0, lon_max=80.0
        ),
        primary_species=["黃鰭鮪", "正鰹", "大目鮪", "旗魚"],
        best_seasons=[1, 2, 3, 10, 11, 12],
        typical_sst_range=(25.0, 30.0),
        notes="季風影響大，需注意海盜風險"
    ),
}


def get_region(region_id: str) -> Optional[FishingRegion]:
    """
    根據 ID 獲取區域定義
    
    Args:
        region_id: 區域識別碼
        
    Returns:
        區域定義，不存在則返回 None
    """
    return FISHING_REGIONS.get(region_id)


def get_region_by_location(lat: float, lon: float) -> List[FishingRegion]:
    """
    根據座標獲取包含該位置的區域
    
    Args:
        lat: 緯度
        lon: 經度
        
    Returns:
        包含該位置的區域列表
    """
    regions = []
    for region in FISHING_REGIONS.values():
        if region.bounds.contains(lat, lon):
            regions.append(region)
    return regions


def get_regions_by_basin(basin: OceanBasin) -> List[FishingRegion]:
    """
    根據海洋盆地獲取區域
    
    Args:
        basin: 海洋盆地
        
    Returns:
        該盆地的區域列表
    """
    return [r for r in FISHING_REGIONS.values() if r.basin == basin]


def get_regions_for_species(species: str) -> List[FishingRegion]:
    """
    根據魚種獲取推薦區域
    
    Args:
        species: 魚種名稱
        
    Returns:
        包含該魚種的區域列表
    """
    return [
        r for r in FISHING_REGIONS.values()
        if species in r.primary_species
    ]


def list_all_regions() -> List[Dict]:
    """
    列出所有區域摘要
    
    Returns:
        區域摘要列表
    """
    return [
        {
            "id": r.id,
            "name": r.name,
            "name_en": r.name_en,
            "basin": r.basin.value,
            "center": r.bounds.center(),
            "primary_species": r.primary_species[:3],
            "best_seasons": r.best_seasons
        }
        for r in FISHING_REGIONS.values()
    ]
