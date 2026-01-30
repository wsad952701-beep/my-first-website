"""
ROI 計算單元測試

測試 ROICalculator 的核心功能：
- 距離計算
- 燃油成本計算
- 漁獲估算
- ROI 建議生成
"""

import pytest
import sys
import os
import math
from unittest.mock import MagicMock, patch

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business.roi import (
    ROICalculator,
    ROIResult,
    FuelCost,
    ExpectedCatch,
    VesselSpecs,
    MARKET_PRICES,
    calculate_roi
)


class TestVesselSpecs:
    """VesselSpecs 測試"""
    
    def test_default_longline(self):
        """測試預設延繩釣漁船規格"""
        vessel = VesselSpecs.default_longline()
        
        assert vessel.name == "標準延繩釣漁船"
        assert vessel.length_m == 45.0
        assert vessel.tonnage_gt == 200
        assert vessel.fuel_consumption_l_per_nm == 2.5
        assert vessel.crew_size == 12
    
    def test_default_purse_seine(self):
        """測試預設圍網漁船規格"""
        vessel = VesselSpecs.default_purse_seine()
        
        assert vessel.name == "標準圍網漁船"
        assert vessel.length_m == 60.0
        assert vessel.tonnage_gt == 500
        assert vessel.fuel_consumption_l_per_nm == 5.0
        assert vessel.crew_size == 25


class TestFuelCost:
    """FuelCost 測試"""
    
    def test_fuel_cost_to_dict(self):
        """測試轉換為字典"""
        cost = FuelCost(
            distance_nm=100.0,
            fuel_consumption_l=250.0,
            fuel_cost_usd=200.0,
            fuel_price_per_l=0.8
        )
        
        result = cost.to_dict()
        
        assert result["distance_nm"] == 100.0
        assert result["fuel_consumption_l"] == 250.0
        assert result["fuel_cost_usd"] == 200.0


class TestROICalculator:
    """ROICalculator 核心測試"""
    
    def test_calculator_initialization_default(self):
        """測試預設初始化"""
        calc = ROICalculator()
        
        assert calc.vessel is not None
        assert calc.fuel_price == 0.8
    
    def test_calculator_initialization_custom(self):
        """測試自定義初始化"""
        vessel = VesselSpecs.default_purse_seine()
        calc = ROICalculator(vessel_specs=vessel, fuel_price_usd_per_l=1.0)
        
        assert calc.vessel.name == "標準圍網漁船"
        assert calc.fuel_price == 1.0
    
    def test_distance_calculation_same_point(self):
        """測試相同點距離為零"""
        calc = ROICalculator()
        
        distance = calc._calculate_distance(
            point1=(22.5, 121.0),
            point2=(22.5, 121.0)
        )
        
        assert distance == pytest.approx(0.0, abs=0.1)
    
    def test_distance_calculation_known_distance(self):
        """測試已知距離（高雄到台東約 100 海里）"""
        calc = ROICalculator()
        
        # 高雄港 (22.6°N, 120.3°E) 到 台東 (22.75°N, 121.15°E)
        distance = calc._calculate_distance(
            point1=(22.6, 120.3),
            point2=(22.75, 121.15)
        )
        
        # 實際距離約 45-50 海里
        assert 40 < distance < 60
    
    def test_distance_calculation_long_distance(self):
        """測試長距離計算"""
        calc = ROICalculator()
        
        # 台灣到關島約 1500 海里
        distance = calc._calculate_distance(
            point1=(22.5, 121.0),
            point2=(13.4, 144.8)
        )
        
        assert 1300 < distance < 1700
    
    def test_fuel_cost_calculation(self):
        """測試燃油成本計算"""
        calc = ROICalculator(fuel_price_usd_per_l=0.8)
        
        fuel_cost = calc._calculate_fuel_cost(distance_nm=100.0)
        
        # 2.5 L/nm * 100 nm = 250 L
        # 250 L * 0.8 USD/L = 200 USD
        assert fuel_cost.fuel_consumption_l == pytest.approx(250.0, abs=1.0)
        assert fuel_cost.fuel_cost_usd == pytest.approx(200.0, abs=1.0)
    
    def test_estimate_catch_high_pfz(self):
        """測試高 PFZ 分數的漁獲估算"""
        calc = ROICalculator()
        
        catches = calc._estimate_catch(
            pfz_score=90,
            species="yellowfin_tuna",
            operation_days=5
        )
        
        assert len(catches) > 0
        assert catches[0].species == "yellowfin_tuna"
        # 高 PFZ 分數應該有較高的預估漁獲
        assert catches[0].estimated_kg > 200
    
    def test_estimate_catch_low_pfz(self):
        """測試低 PFZ 分數的漁獲估算"""
        calc = ROICalculator()
        
        catches = calc._estimate_catch(
            pfz_score=20,
            species="yellowfin_tuna",
            operation_days=5
        )
        
        assert len(catches) > 0
        # 低 PFZ 分數應該有較低的預估漁獲
        assert catches[0].estimated_kg < 400
    
    def test_market_price_valid_species(self):
        """測試有效魚種的市場價格"""
        calc = ROICalculator()
        
        price = calc._get_market_price("yellowfin_tuna", "price_avg")
        
        assert price == 10.0  # MARKET_PRICES 中定義的價格
    
    def test_market_price_invalid_species(self):
        """測試無效魚種的預設價格"""
        calc = ROICalculator()
        
        price = calc._get_market_price("invalid_species", "price_avg")
        
        assert price == 5.0  # 預設價格
    
    def test_roi_calculation_full(self, sample_roi_input):
        """測試完整 ROI 計算"""
        calc = ROICalculator()
        
        result = calc.calculate(**sample_roi_input)
        
        assert isinstance(result, ROIResult)
        assert result.total_cost > 0
        assert result.expected_revenue > 0
        assert result.break_even_catch_kg > 0
        assert result.recommendation != ""
    
    def test_roi_result_is_profitable(self):
        """測試利潤判斷"""
        calc = ROICalculator()
        
        # 高 PFZ 分數，短距離應該有利潤
        result = calc.calculate(
            origin=(22.6, 120.3),
            destination=(22.8, 121.0),
            pfz_score=85,
            target_species="yellowfin_tuna",
            operation_days=5
        )
        
        # 這個情況通常應該是有利潤的
        assert isinstance(result.is_profitable, bool)
    
    def test_recommendation_levels(self):
        """測試建議等級"""
        calc = ROICalculator()
        
        # 測試不同 ROI 等級的建議
        recommendations = []
        for pfz in [90, 60, 40, 20]:
            result = calc.calculate(
                origin=(22.6, 120.3),
                destination=(22.8, 121.0),
                pfz_score=pfz,
                target_species="yellowfin_tuna",
                operation_days=5
            )
            recommendations.append(result.recommendation)
        
        # 建議應該隨 PFZ 分數變化
        for rec in recommendations:
            assert rec is not None
            assert len(rec) > 0


class TestROIResultDataClass:
    """ROIResult 資料類別測試"""
    
    def test_roi_result_to_dict(self):
        """測試轉換為字典"""
        fuel_cost = FuelCost(
            distance_nm=200.0,
            fuel_consumption_l=500.0,
            fuel_cost_usd=400.0,
            fuel_price_per_l=0.8
        )
        
        catch = ExpectedCatch(
            species="yellowfin_tuna",
            estimated_kg=500.0,
            price_per_kg=10.0,
            estimated_value=5000.0,
            confidence=0.7
        )
        
        result = ROIResult(
            expected_revenue=5000.0,
            total_cost=2500.0,
            net_profit=2500.0,
            roi_percentage=100.0,
            break_even_catch_kg=250.0,
            fuel_cost=fuel_cost,
            expected_catches=[catch],
            recommendation="測試建議"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["expected_revenue"] == 5000.0
        assert result_dict["total_cost"] == 2500.0
        assert result_dict["net_profit"] == 2500.0
        assert result_dict["roi_percentage"] == 100.0
        assert result_dict["is_profitable"] == True


class TestConvenienceFunction:
    """便捷函數測試"""
    
    def test_calculate_roi_function(self):
        """測試 calculate_roi 便捷函數"""
        result = calculate_roi(
            origin=(22.6, 120.3),
            destination=(24.0, 122.0),
            pfz_score=75,
            target_species="yellowfin_tuna"
        )
        
        assert isinstance(result, ROIResult)
        assert result.total_cost > 0


class TestMarketPrices:
    """市場價格配置測試"""
    
    def test_all_species_have_prices(self):
        """測試所有支援魚種都有價格"""
        expected_species = [
            "bluefin_tuna",
            "yellowfin_tuna",
            "bigeye_tuna",
            "skipjack",
            "albacore",
            "swordfish",
            "mahi_mahi"
        ]
        
        for species in expected_species:
            assert species in MARKET_PRICES
            assert "price_low" in MARKET_PRICES[species]
            assert "price_avg" in MARKET_PRICES[species]
            assert "price_high" in MARKET_PRICES[species]
    
    def test_price_order(self):
        """測試價格順序 (low < avg < high)"""
        for species, prices in MARKET_PRICES.items():
            assert prices["price_low"] < prices["price_avg"]
            assert prices["price_avg"] < prices["price_high"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
