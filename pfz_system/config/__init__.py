"""
PFZ Config Module

提供系統配置、區域定義與魚種資料。
"""

try:
    from .settings import Settings, get_settings, configure_logging
    from .regions import (
        FishingRegion,
        RegionBounds,
        OceanBasin,
        FISHING_REGIONS,
        get_region,
        get_region_by_location,
        get_regions_by_basin,
        list_all_regions
    )
    from .species import (
        Species,
        FishCategory,
        SPECIES,
        get_species,
        get_species_by_category,
        get_species_for_temperature,
        list_all_species
    )
except ImportError:
    from settings import Settings, get_settings, configure_logging
    from regions import (
        FishingRegion,
        RegionBounds,
        OceanBasin,
        FISHING_REGIONS,
        get_region,
        get_region_by_location,
        get_regions_by_basin,
        list_all_regions
    )
    from species import (
        Species,
        FishCategory,
        SPECIES,
        get_species,
        get_species_by_category,
        get_species_for_temperature,
        list_all_species
    )

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "configure_logging",
    # Regions
    "FishingRegion",
    "RegionBounds",
    "OceanBasin",
    "FISHING_REGIONS",
    "get_region",
    "get_region_by_location",
    "get_regions_by_basin",
    "list_all_regions",
    # Species
    "Species",
    "FishCategory",
    "SPECIES",
    "get_species",
    "get_species_by_category",
    "get_species_for_temperature",
    "list_all_species",
]
