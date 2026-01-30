"""
ROI (投資報酬率) 計算模組

評估漁業作業的經濟效益，包括：
- 燃油成本估算
- 預期漁獲價值
- 航程規劃優化
- 整體 ROI 分析
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FuelCost:
    """燃油成本"""
    distance_nm: float           # 航程 (海里)
    fuel_consumption_l: float    # 燃油消耗 (公升)
    fuel_cost_usd: float         # 燃油費用 (USD)
    fuel_price_per_l: float      # 燃油單價 (USD/L)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "distance_nm": self.distance_nm,
            "fuel_consumption_l": self.fuel_consumption_l,
            "fuel_cost_usd": self.fuel_cost_usd,
            "fuel_price_per_l": self.fuel_price_per_l
        }


@dataclass
class ExpectedCatch:
    """預期漁獲"""
    species: str
    estimated_kg: float
    price_per_kg: float
    estimated_value: float
    confidence: float  # 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "species": self.species,
            "estimated_kg": self.estimated_kg,
            "price_per_kg": self.price_per_kg,
            "estimated_value": self.estimated_value,
            "confidence": self.confidence
        }


@dataclass 
class ROIResult:
    """
    ROI 分析結果
    
    Attributes:
        expected_revenue: 預期收入
        total_cost: 總成本
        net_profit: 淨利潤
        roi_percentage: ROI 百分比
        break_even_catch: 損益平衡漁獲量
        recommendation: 建議
    """
    expected_revenue: float
    total_cost: float
    net_profit: float
    roi_percentage: float
    break_even_catch_kg: float
    fuel_cost: FuelCost
    expected_catches: List[ExpectedCatch]
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_profitable(self) -> bool:
        """是否預期有利潤"""
        return self.net_profit > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_revenue": self.expected_revenue,
            "total_cost": self.total_cost,
            "net_profit": self.net_profit,
            "roi_percentage": self.roi_percentage,
            "break_even_catch_kg": self.break_even_catch_kg,
            "is_profitable": self.is_profitable,
            "fuel_cost": self.fuel_cost.to_dict(),
            "expected_catches": [c.to_dict() for c in self.expected_catches],
            "recommendation": self.recommendation
        }


@dataclass
class VesselSpecs:
    """船舶規格"""
    name: str
    length_m: float
    tonnage_gt: float
    engine_hp: float
    fuel_consumption_l_per_nm: float  # 每海里燃油消耗
    crew_size: int
    operating_cost_per_day: float     # 每日營運成本 (USD)
    
    @classmethod
    def default_longline(cls) -> "VesselSpecs":
        """預設延繩釣漁船規格"""
        return cls(
            name="標準延繩釣漁船",
            length_m=45.0,
            tonnage_gt=200,
            engine_hp=800,
            fuel_consumption_l_per_nm=2.5,
            crew_size=12,
            operating_cost_per_day=500
        )
    
    @classmethod
    def default_purse_seine(cls) -> "VesselSpecs":
        """預設圍網漁船規格"""
        return cls(
            name="標準圍網漁船",
            length_m=60.0,
            tonnage_gt=500,
            engine_hp=2000,
            fuel_consumption_l_per_nm=5.0,
            crew_size=25,
            operating_cost_per_day=1500
        )


# 魚種市場價格 (USD/kg)
MARKET_PRICES: Dict[str, Dict[str, float]] = {
    "bluefin_tuna": {
        "price_low": 20.0,
        "price_avg": 40.0,
        "price_high": 80.0
    },
    "yellowfin_tuna": {
        "price_low": 6.0,
        "price_avg": 10.0,
        "price_high": 15.0
    },
    "bigeye_tuna": {
        "price_low": 8.0,
        "price_avg": 12.0,
        "price_high": 18.0
    },
    "skipjack": {
        "price_low": 1.5,
        "price_avg": 2.5,
        "price_high": 4.0
    },
    "albacore": {
        "price_low": 4.0,
        "price_avg": 6.0,
        "price_high": 9.0
    },
    "swordfish": {
        "price_low": 8.0,
        "price_avg": 12.0,
        "price_high": 18.0
    },
    "mahi_mahi": {
        "price_low": 5.0,
        "price_avg": 8.0,
        "price_high": 12.0
    }
}


class ROICalculator:
    """
    ROI 計算器
    
    評估漁業作業的經濟效益。
    
    Example:
        >>> calc = ROICalculator()
        >>> result = calc.calculate(
        ...     origin=(22.6, 120.3),
        ...     destination=(24.0, 122.0),
        ...     pfz_score=75,
        ...     target_species="yellowfin_tuna"
        ... )
        >>> print(f"ROI: {result.roi_percentage}%")
    """
    
    def __init__(
        self,
        vessel_specs: Optional[VesselSpecs] = None,
        fuel_price_usd_per_l: float = 0.8
    ):
        """
        初始化 ROI 計算器
        
        Args:
            vessel_specs: 船舶規格
            fuel_price_usd_per_l: 燃油價格 (USD/L)
        """
        self.vessel = vessel_specs or VesselSpecs.default_longline()
        self.fuel_price = fuel_price_usd_per_l
    
    def calculate(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        pfz_score: float,
        target_species: str,
        operation_days: int = 5
    ) -> ROIResult:
        """
        計算 ROI
        
        Args:
            origin: 出發點 (lat, lon)
            destination: 目標漁場 (lat, lon)
            pfz_score: PFZ 分數 (0-100)
            target_species: 目標魚種
            operation_days: 作業天數
            
        Returns:
            ROIResult
        """
        # 1. 計算燃油成本
        distance = self._calculate_distance(origin, destination)
        total_distance = distance * 2  # 來回
        fuel_cost = self._calculate_fuel_cost(total_distance)
        
        # 2. 計算營運成本
        operating_cost = self.vessel.operating_cost_per_day * operation_days
        total_cost = fuel_cost.fuel_cost_usd + operating_cost
        
        # 3. 估算漁獲
        expected_catches = self._estimate_catch(
            pfz_score, target_species, operation_days
        )
        
        # 4. 計算預期收入
        expected_revenue = sum(c.estimated_value for c in expected_catches)
        
        # 5. 計算淨利潤與 ROI
        net_profit = expected_revenue - total_cost
        roi_percentage = (net_profit / total_cost * 100) if total_cost > 0 else 0
        
        # 6. 計算損益平衡點
        avg_price = self._get_market_price(target_species, "price_avg")
        break_even_kg = total_cost / avg_price if avg_price > 0 else float('inf')
        
        # 7. 生成建議
        recommendation = self._generate_recommendation(
            roi_percentage, net_profit, pfz_score, distance
        )
        
        return ROIResult(
            expected_revenue=round(expected_revenue, 2),
            total_cost=round(total_cost, 2),
            net_profit=round(net_profit, 2),
            roi_percentage=round(roi_percentage, 1),
            break_even_catch_kg=round(break_even_kg, 1),
            fuel_cost=fuel_cost,
            expected_catches=expected_catches,
            recommendation=recommendation,
            details={
                "distance_nm": distance,
                "operation_days": operation_days,
                "operating_cost": operating_cost,
                "vessel": self.vessel.name
            }
        )
    
    def _calculate_distance(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        """計算兩點距離 (海里)"""
        lat1, lon1 = np.radians(point1)
        lat2, lon2 = np.radians(point2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        R_nm = 3440.065  # 地球半徑 (海里)
        return R_nm * c
    
    def _calculate_fuel_cost(self, distance_nm: float) -> FuelCost:
        """計算燃油成本"""
        consumption = distance_nm * self.vessel.fuel_consumption_l_per_nm
        cost = consumption * self.fuel_price
        
        return FuelCost(
            distance_nm=round(distance_nm, 1),
            fuel_consumption_l=round(consumption, 1),
            fuel_cost_usd=round(cost, 2),
            fuel_price_per_l=self.fuel_price
        )
    
    def _estimate_catch(
        self,
        pfz_score: float,
        species: str,
        operation_days: int
    ) -> List[ExpectedCatch]:
        """
        估算漁獲量
        
        基於 PFZ 分數和歷史 CPUE 數據
        """
        # 基礎 CPUE (kg/天) 根據魚種
        base_cpue = {
            "bluefin_tuna": 30,
            "yellowfin_tuna": 80,
            "bigeye_tuna": 50,
            "skipjack": 500,
            "albacore": 100,
            "swordfish": 40,
            "mahi_mahi": 60
        }
        
        cpue = base_cpue.get(species, 50)
        
        # PFZ 分數調整 (分數越高，預期漁獲越多)
        pfz_factor = 0.5 + (pfz_score / 100) * 1.0  # 0.5-1.5
        
        # 隨機變異 (模擬)
        variability = np.random.normal(1.0, 0.2)
        variability = max(0.5, min(1.5, variability))
        
        estimated_kg = cpue * operation_days * pfz_factor * variability
        
        price = self._get_market_price(species, "price_avg")
        estimated_value = estimated_kg * price
        
        # 信心度與 PFZ 分數相關
        confidence = min(0.9, 0.3 + pfz_score / 150)
        
        return [ExpectedCatch(
            species=species,
            estimated_kg=round(estimated_kg, 1),
            price_per_kg=price,
            estimated_value=round(estimated_value, 2),
            confidence=round(confidence, 2)
        )]
    
    def _get_market_price(
        self,
        species: str,
        price_type: str = "price_avg"
    ) -> float:
        """獲取市場價格"""
        prices = MARKET_PRICES.get(species, {"price_avg": 5.0})
        return prices.get(price_type, 5.0)
    
    def _generate_recommendation(
        self,
        roi: float,
        profit: float,
        pfz_score: float,
        distance: float
    ) -> str:
        """生成建議"""
        if roi >= 100:
            rec = "💰 極佳投資！預期回報優異，強烈建議出航。"
        elif roi >= 50:
            rec = "✅ 良好投資。預期有合理回報。"
        elif roi >= 20:
            rec = "⚠️ 中等投資。利潤有限，需評估風險。"
        elif roi >= 0:
            rec = "⚡ 邊際投資。可能接近損益平衡。"
        else:
            rec = "❌ 不建議。預期虧損，考慮其他漁場。"
        
        # 添加額外建議
        if distance > 500:
            rec += " 航程較遠，注意燃油儲備。"
        
        if pfz_score < 50:
            rec += " PFZ 分數偏低，漁況可能不佳。"
        
        return rec


def calculate_roi(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    pfz_score: float,
    target_species: str = "yellowfin_tuna"
) -> ROIResult:
    """
    便捷函數：計算 ROI
    
    Args:
        origin: 出發點
        destination: 目標漁場
        pfz_score: PFZ 分數
        target_species: 目標魚種
        
    Returns:
        ROIResult
    """
    calc = ROICalculator()
    return calc.calculate(origin, destination, pfz_score, target_species)
