"""
魚種定義與棲息特性

定義各目標魚種的：
- 環境偏好 (溫度、鹽度、深度)
- 行為特性
- 季節性模式
- 最佳捕捉條件
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class FishCategory(Enum):
    """魚類分類"""
    TUNA = "tuna"                 # 鮪魚類
    BILLFISH = "billfish"         # 旗魚類
    PELAGIC = "pelagic"           # 大洋洄游魚
    COASTAL = "coastal"           # 沿海魚類
    SQUID = "squid"               # 魷魚/頭足類
    SHRIMP_CRAB = "shrimp_crab"   # 蝦蟹類


class MigrationPattern(Enum):
    """洄游模式"""
    RESIDENT = "resident"         # 定棲性
    SEASONAL = "seasonal"         # 季節性洄游
    TRANS_OCEANIC = "trans_oceanic"  # 跨洋洄游


@dataclass
class TemperaturePreference:
    """溫度偏好"""
    optimal_min: float  # 最佳溫度下限 (°C)
    optimal_max: float  # 最佳溫度上限 (°C)
    tolerance_min: float  # 可容忍下限 (°C)
    tolerance_max: float  # 可容忍上限 (°C)
    
    def is_optimal(self, temp: float) -> bool:
        """是否在最佳範圍"""
        return self.optimal_min <= temp <= self.optimal_max
    
    def is_tolerable(self, temp: float) -> bool:
        """是否在可容忍範圍"""
        return self.tolerance_min <= temp <= self.tolerance_max
    
    def preference_score(self, temp: float) -> float:
        """
        計算溫度偏好分數 (0-100)
        """
        if self.is_optimal(temp):
            return 100.0
        elif self.is_tolerable(temp):
            if temp < self.optimal_min:
                return 100 * (temp - self.tolerance_min) / (self.optimal_min - self.tolerance_min)
            else:
                return 100 * (self.tolerance_max - temp) / (self.tolerance_max - self.optimal_max)
        else:
            return 0.0


@dataclass
class DepthPreference:
    """深度偏好"""
    day_min: float      # 白天最小深度 (m)
    day_max: float      # 白天最大深度 (m)
    night_min: float    # 夜間最小深度 (m)
    night_max: float    # 夜間最大深度 (m)
    notes: str = ""


@dataclass
class Species:
    """
    魚種定義
    
    Attributes:
        id: 魚種識別碼
        name_zh: 中文名
        name_en: 英文名
        name_scientific: 學名
        category: 魚類分類
        temperature: 溫度偏好
        depth: 深度偏好
        chla_preference: 葉綠素偏好 (mg/m³)
        migration: 洄游模式
        peak_seasons: 旺季月份
        fishing_methods: 適用漁法
        notes: 備註
    """
    id: str
    name_zh: str
    name_en: str
    name_scientific: str
    category: FishCategory
    temperature: TemperaturePreference
    depth: Optional[DepthPreference] = None
    chla_preference: Tuple[float, float] = (0.1, 1.0)  # mg/m³
    migration: MigrationPattern = MigrationPattern.SEASONAL
    peak_seasons: List[int] = field(default_factory=list)
    fishing_methods: List[str] = field(default_factory=list)
    notes: str = ""
    
    def get_habitat_score(
        self,
        sst: float,
        chla: Optional[float] = None
    ) -> float:
        """
        計算棲息地適宜度分數
        
        Args:
            sst: 海表溫度 (°C)
            chla: 葉綠素濃度 (mg/m³)
            
        Returns:
            0-100 分數
        """
        # 溫度分數 (權重 70%)
        temp_score = self.temperature.preference_score(sst)
        
        # 葉綠素分數 (權重 30%)
        if chla is not None:
            chla_min, chla_max = self.chla_preference
            if chla_min <= chla <= chla_max:
                chla_score = 100.0
            elif chla < chla_min:
                chla_score = max(0, 100 * chla / chla_min)
            else:
                chla_score = max(0, 100 * (2 - chla / chla_max))
        else:
            chla_score = 50.0  # 無數據時給予中等分數
        
        return 0.7 * temp_score + 0.3 * chla_score


# ============================================
# 預定義魚種
# ============================================

SPECIES: Dict[str, Species] = {
    # 鮪魚類
    "bluefin_tuna": Species(
        id="bluefin_tuna",
        name_zh="太平洋黑鮪",
        name_en="Pacific Bluefin Tuna",
        name_scientific="Thunnus orientalis",
        category=FishCategory.TUNA,
        temperature=TemperaturePreference(
            optimal_min=18.0, optimal_max=24.0,
            tolerance_min=12.0, tolerance_max=28.0
        ),
        depth=DepthPreference(
            day_min=50, day_max=200,
            night_min=0, night_max=50,
            notes="晝夜垂直洄游"
        ),
        chla_preference=(0.1, 0.5),
        migration=MigrationPattern.TRANS_OCEANIC,
        peak_seasons=[4, 5, 6, 7],
        fishing_methods=["延繩釣", "圍網"],
        notes="高經濟價值，春季洄游至台灣東部"
    ),
    
    "yellowfin_tuna": Species(
        id="yellowfin_tuna",
        name_zh="黃鰭鮪",
        name_en="Yellowfin Tuna",
        name_scientific="Thunnus albacares",
        category=FishCategory.TUNA,
        temperature=TemperaturePreference(
            optimal_min=24.0, optimal_max=28.0,
            tolerance_min=18.0, tolerance_max=31.0
        ),
        depth=DepthPreference(
            day_min=50, day_max=250,
            night_min=0, night_max=100
        ),
        chla_preference=(0.1, 0.8),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=list(range(1, 13)),  # 全年
        fishing_methods=["延繩釣", "圍網", "竿釣"],
        notes="熱帶海域全年可捕獲"
    ),
    
    "bigeye_tuna": Species(
        id="bigeye_tuna",
        name_zh="大目鮪",
        name_en="Bigeye Tuna",
        name_scientific="Thunnus obesus",
        category=FishCategory.TUNA,
        temperature=TemperaturePreference(
            optimal_min=17.0, optimal_max=22.0,
            tolerance_min=10.0, tolerance_max=28.0
        ),
        depth=DepthPreference(
            day_min=200, day_max=500,
            night_min=50, night_max=200,
            notes="深海棲息，夜間上浮"
        ),
        chla_preference=(0.1, 0.5),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=[9, 10, 11, 12, 1, 2],
        fishing_methods=["延繩釣"],
        notes="偏好較低溫深水層"
    ),
    
    "albacore": Species(
        id="albacore",
        name_zh="長鰭鮪",
        name_en="Albacore",
        name_scientific="Thunnus alalunga",
        category=FishCategory.TUNA,
        temperature=TemperaturePreference(
            optimal_min=15.0, optimal_max=21.0,
            tolerance_min=10.0, tolerance_max=25.0
        ),
        depth=DepthPreference(
            day_min=100, day_max=300,
            night_min=0, night_max=100
        ),
        chla_preference=(0.1, 0.6),
        migration=MigrationPattern.TRANS_OCEANIC,
        peak_seasons=[3, 4, 5, 9, 10, 11],
        fishing_methods=["延繩釣", "曳繩釣"],
        notes="溫帶種，偏好鋒面區域"
    ),
    
    "skipjack": Species(
        id="skipjack",
        name_zh="正鰹",
        name_en="Skipjack Tuna",
        name_scientific="Katsuwonus pelamis",
        category=FishCategory.TUNA,
        temperature=TemperaturePreference(
            optimal_min=26.0, optimal_max=30.0,
            tolerance_min=20.0, tolerance_max=32.0
        ),
        depth=DepthPreference(
            day_min=0, day_max=100,
            night_min=0, night_max=50
        ),
        chla_preference=(0.2, 1.0),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=list(range(1, 13)),
        fishing_methods=["圍網", "竿釣"],
        notes="表層魚種，適合圍網作業"
    ),
    
    # 旗魚類
    "blue_marlin": Species(
        id="blue_marlin",
        name_zh="黑皮旗魚",
        name_en="Blue Marlin",
        name_scientific="Makaira nigricans",
        category=FishCategory.BILLFISH,
        temperature=TemperaturePreference(
            optimal_min=24.0, optimal_max=29.0,
            tolerance_min=20.0, tolerance_max=31.0
        ),
        depth=DepthPreference(
            day_min=0, day_max=200,
            night_min=0, night_max=100
        ),
        chla_preference=(0.05, 0.3),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=[7, 8, 9, 10],
        fishing_methods=["延繩釣", "鏢旗魚"],
        notes="大型遊釣魚類"
    ),
    
    "swordfish": Species(
        id="swordfish",
        name_zh="劍旗魚",
        name_en="Swordfish",
        name_scientific="Xiphias gladius",
        category=FishCategory.BILLFISH,
        temperature=TemperaturePreference(
            optimal_min=18.0, optimal_max=22.0,
            tolerance_min=10.0, tolerance_max=28.0
        ),
        depth=DepthPreference(
            day_min=200, day_max=600,
            night_min=0, night_max=100,
            notes="夜間浮至表層覓食"
        ),
        chla_preference=(0.1, 0.5),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=[10, 11, 12, 1, 2, 3],
        fishing_methods=["延繩釣", "鏢旗魚"],
        notes="秋冬季較活躍"
    ),
    
    # 洄游魚類
    "mahi_mahi": Species(
        id="mahi_mahi",
        name_zh="鬼頭刀",
        name_en="Mahi-mahi",
        name_scientific="Coryphaena hippurus",
        category=FishCategory.PELAGIC,
        temperature=TemperaturePreference(
            optimal_min=25.0, optimal_max=29.0,
            tolerance_min=21.0, tolerance_max=31.0
        ),
        depth=DepthPreference(
            day_min=0, day_max=50,
            night_min=0, night_max=30
        ),
        chla_preference=(0.1, 0.8),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=[4, 5, 6, 7, 8, 9],
        fishing_methods=["延繩釣", "曳繩釣", "竿釣"],
        notes="常聚集於漂流物下方"
    ),
    
    # 魷魚
    "flying_squid": Species(
        id="flying_squid",
        name_zh="赤魷",
        name_en="Japanese Flying Squid",
        name_scientific="Todarodes pacificus",
        category=FishCategory.SQUID,
        temperature=TemperaturePreference(
            optimal_min=15.0, optimal_max=20.0,
            tolerance_min=10.0, tolerance_max=25.0
        ),
        depth=DepthPreference(
            day_min=100, day_max=300,
            night_min=0, night_max=50,
            notes="夜間趨光上浮"
        ),
        chla_preference=(0.3, 1.5),
        migration=MigrationPattern.SEASONAL,
        peak_seasons=[6, 7, 8, 9, 10],
        fishing_methods=["魷釣"],
        notes="使用集魚燈作業"
    ),
}


def get_species(species_id: str) -> Optional[Species]:
    """
    根據 ID 獲取魚種定義
    
    Args:
        species_id: 魚種識別碼
        
    Returns:
        魚種定義，不存在則返回 None
    """
    return SPECIES.get(species_id)


def get_species_by_category(category: FishCategory) -> List[Species]:
    """
    根據分類獲取魚種列表
    
    Args:
        category: 魚類分類
        
    Returns:
        該分類的魚種列表
    """
    return [s for s in SPECIES.values() if s.category == category]


def get_species_for_temperature(sst: float, min_score: float = 50.0) -> List[Tuple[Species, float]]:
    """
    根據溫度獲取適合的魚種
    
    Args:
        sst: 海表溫度 (°C)
        min_score: 最低適宜度分數
        
    Returns:
        [(魚種, 分數), ...] 按分數降序排列
    """
    results = []
    for species in SPECIES.values():
        score = species.get_habitat_score(sst)
        if score >= min_score:
            results.append((species, score))
    
    return sorted(results, key=lambda x: x[1], reverse=True)


def list_all_species() -> List[Dict]:
    """
    列出所有魚種摘要
    
    Returns:
        魚種摘要列表
    """
    return [
        {
            "id": s.id,
            "name_zh": s.name_zh,
            "name_en": s.name_en,
            "category": s.category.value,
            "optimal_sst": (s.temperature.optimal_min, s.temperature.optimal_max),
            "peak_seasons": s.peak_seasons,
            "fishing_methods": s.fishing_methods
        }
        for s in SPECIES.values()
    ]
