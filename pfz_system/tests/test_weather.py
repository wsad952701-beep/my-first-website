"""
氣象模組單元測試

測試氣象數據獲取與作業適宜度計算：
- Open-Meteo API 整合
- 多國模型預報比較
- 作業適宜度評估
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather.operability import OperabilityCalculator, OperabilityResult, VesselType


class TestVesselType:
    """VesselType 枚舉測試"""
    
    def test_vessel_types_exist(self):
        """測試船型枚舉存在"""
        assert hasattr(VesselType, 'LONGLINE')
        assert hasattr(VesselType, 'PURSE_SEINE')
        assert hasattr(VesselType, 'TRAWLER')
        assert hasattr(VesselType, 'GILLNET')


class TestOperabilityCalculator:
    """OperabilityCalculator 測試"""
    
    def test_calculator_initialization(self):
        """測試計算器初始化"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        assert calc.vessel_type == VesselType.LONGLINE
    
    def test_calm_conditions_high_operability(self):
        """測試平靜條件下的高適宜度"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        # 模擬平靜的海況
        result = calc.calculate(
            wind_speed=5.0,      # 微風
            wave_height=0.5,     # 平靜
            precipitation=0.0,   # 無雨
            visibility=10.0      # 良好能見度
        )
        
        assert result.score >= 80
        assert result.is_operable == True
    
    def test_storm_conditions_low_operability(self):
        """測試惡劣條件下的低適宜度"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        # 模擬暴風雨
        result = calc.calculate(
            wind_speed=25.0,     # 強風
            wave_height=4.0,     # 大浪
            precipitation=20.0,  # 大雨
            visibility=1.0       # 能見度差
        )
        
        assert result.score <= 30
        assert result.is_operable == False
    
    def test_different_vessel_thresholds(self):
        """測試不同船型的閾值差異"""
        conditions = {
            "wind_speed": 15.0,
            "wave_height": 2.5,
            "precipitation": 5.0,
            "visibility": 5.0
        }
        
        longline_calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        seine_calc = OperabilityCalculator(vessel_type=VesselType.PURSE_SEINE)
        
        longline_result = longline_calc.calculate(**conditions)
        seine_result = seine_calc.calculate(**conditions)
        
        # 圍網作業對海況要求更高
        # 兩者都應該有分數，但可能不同
        assert longline_result.score is not None
        assert seine_result.score is not None
    
    def test_operability_result_details(self):
        """測試結果包含詳細資訊"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        result = calc.calculate(
            wind_speed=10.0,
            wave_height=1.5,
            precipitation=2.0,
            visibility=8.0
        )
        
        assert hasattr(result, 'score')
        assert hasattr(result, 'is_operable')
        assert hasattr(result, 'limiting_factor')
        assert hasattr(result, 'recommendation')


class TestOperabilityResult:
    """OperabilityResult 資料類別測試"""
    
    def test_result_creation(self):
        """測試結果物件建立"""
        result = OperabilityResult(
            score=75.0,
            is_operable=True,
            limiting_factor="wave_height",
            wind_score=80.0,
            wave_score=70.0,
            precipitation_score=90.0,
            visibility_score=85.0,
            recommendation="適宜作業"
        )
        
        assert result.score == 75.0
        assert result.is_operable == True
        assert result.limiting_factor == "wave_height"


class TestWeatherThresholds:
    """氣象閾值測試"""
    
    def test_wind_thresholds(self):
        """測試風速閾值"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        # 微風 (0-10 kt) 應該沒問題
        light_wind = calc.calculate(wind_speed=5.0, wave_height=0.5, precipitation=0, visibility=10)
        assert light_wind.wind_score >= 90
        
        # 強風 (>25 kt) 應該很低
        strong_wind = calc.calculate(wind_speed=30.0, wave_height=0.5, precipitation=0, visibility=10)
        assert strong_wind.wind_score <= 30
    
    def test_wave_thresholds(self):
        """測試浪高閾值"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        # 平靜 (0-1m) 應該沒問題
        calm = calc.calculate(wind_speed=5.0, wave_height=0.5, precipitation=0, visibility=10)
        assert calm.wave_score >= 90
        
        # 大浪 (>3m) 應該很低
        rough = calc.calculate(wind_speed=5.0, wave_height=4.0, precipitation=0, visibility=10)
        assert rough.wave_score <= 30


class TestMultiDayForecast:
    """多日預報測試"""
    
    def test_forecast_aggregation(self):
        """測試預報彙總"""
        calc = OperabilityCalculator(vessel_type=VesselType.LONGLINE)
        
        # 模擬多日預報數據
        forecast_data = [
            {"wind_speed": 8.0, "wave_height": 1.0, "precipitation": 0, "visibility": 10},
            {"wind_speed": 12.0, "wave_height": 1.5, "precipitation": 2, "visibility": 8},
            {"wind_speed": 15.0, "wave_height": 2.0, "precipitation": 5, "visibility": 6},
        ]
        
        results = []
        for day_data in forecast_data:
            result = calc.calculate(**day_data)
            results.append(result)
        
        # 天氣惡化，分數應該遞減
        assert len(results) == 3
        # 第一天應該比第三天好
        assert results[0].score >= results[2].score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
