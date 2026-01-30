"""
PFZ 核心算法單元測試

測試 PFZCalculator 的核心功能：
- 分數計算邏輯
- 棲息地評估
- 建議生成
- 邊界條件處理
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.pfz import PFZCalculator, PFZScore, PFZPrediction


class TestPFZScore:
    """PFZScore 資料類別測試"""
    
    def test_score_creation(self):
        """測試分數物件建立"""
        score = PFZScore(
            total_score=75.0,
            habitat_score=80.0,
            front_score=70.0,
            eddy_score=65.0,
            weather_score=85.0,
            trend_score=75.0,
            confidence=0.72,
            recommendation="測試建議"
        )
        
        assert score.total_score == 75.0
        assert score.habitat_score == 80.0
        assert score.confidence == 0.72
    
    def test_score_level_excellent(self):
        """測試優良等級"""
        score = PFZScore(
            total_score=85.0,
            habitat_score=85.0,
            front_score=85.0,
            eddy_score=85.0,
            weather_score=85.0,
            trend_score=85.0,
            confidence=0.9,
            recommendation=""
        )
        assert score.level == "優良"
    
    def test_score_level_good(self):
        """測試良好等級"""
        score = PFZScore(
            total_score=70.0,
            habitat_score=70.0,
            front_score=70.0,
            eddy_score=70.0,
            weather_score=70.0,
            trend_score=70.0,
            confidence=0.7,
            recommendation=""
        )
        assert score.level == "良好"
    
    def test_score_level_moderate(self):
        """測試中等等級"""
        score = PFZScore(
            total_score=55.0,
            habitat_score=55.0,
            front_score=55.0,
            eddy_score=55.0,
            weather_score=55.0,
            trend_score=55.0,
            confidence=0.5,
            recommendation=""
        )
        assert score.level == "中等"
    
    def test_score_level_poor(self):
        """測試不佳等級"""
        score = PFZScore(
            total_score=35.0,
            habitat_score=35.0,
            front_score=35.0,
            eddy_score=35.0,
            weather_score=35.0,
            trend_score=35.0,
            confidence=0.3,
            recommendation=""
        )
        assert score.level == "不佳"
    
    def test_score_color(self):
        """測試等級顏色"""
        excellent = PFZScore(
            total_score=85.0, habitat_score=85.0, front_score=85.0,
            eddy_score=85.0, weather_score=85.0, trend_score=85.0,
            confidence=0.9, recommendation=""
        )
        assert excellent.color == "#22C55E"  # 綠色
        
        poor = PFZScore(
            total_score=25.0, habitat_score=25.0, front_score=25.0,
            eddy_score=25.0, weather_score=25.0, trend_score=25.0,
            confidence=0.3, recommendation=""
        )
        assert poor.color == "#EF4444"  # 紅色


class TestPFZCalculator:
    """PFZCalculator 核心測試"""
    
    def test_calculator_initialization_default(self):
        """測試預設初始化"""
        calc = PFZCalculator()
        
        assert calc.weights is not None
        assert "habitat" in calc.weights
        assert "front" in calc.weights
        assert "eddy" in calc.weights
        assert "weather" in calc.weights
    
    def test_calculator_initialization_with_species(self):
        """測試指定魚種初始化"""
        calc = PFZCalculator(target_species="yellowfin_tuna")
        
        assert calc.species == "yellowfin_tuna"
    
    def test_calculator_initialization_with_custom_weights(self):
        """測試自定義權重"""
        custom_weights = {
            "habitat": 0.5,
            "front": 0.2,
            "eddy": 0.1,
            "weather": 0.2,
            "trend": 0.0
        }
        calc = PFZCalculator(weights=custom_weights)
        
        assert calc.weights["habitat"] == 0.5
        assert calc.weights["front"] == 0.2
    
    def test_weights_sum_to_one(self):
        """測試權重總和為 1"""
        calc = PFZCalculator()
        total_weight = sum(calc.weights.values())
        
        assert abs(total_weight - 1.0) < 0.01, f"Weights sum to {total_weight}, not 1.0"
    
    @patch.object(PFZCalculator, '_get_sst')
    @patch.object(PFZCalculator, '_get_chla')
    @patch.object(PFZCalculator, '_detect_fronts')
    @patch.object(PFZCalculator, '_detect_eddies')
    @patch.object(PFZCalculator, '_get_weather')
    def test_predict_returns_prediction(
        self, mock_weather, mock_eddies, mock_fronts, mock_chla, mock_sst
    ):
        """測試預測返回 PFZPrediction 物件"""
        # 設置 mock 返回值
        mock_sst.return_value = 26.5
        mock_chla.return_value = 0.35
        mock_fronts.return_value = MagicMock(front_score=70.0)
        mock_eddies.return_value = MagicMock(eddy_score=65.0)
        mock_weather.return_value = MagicMock(operability_score=80.0)
        
        calc = PFZCalculator(target_species="yellowfin_tuna")
        prediction = calc.predict(lat=22.5, lon=121.0)
        
        assert isinstance(prediction, PFZPrediction)
        assert prediction.lat == 22.5
        assert prediction.lon == 121.0
        assert prediction.score is not None
    
    def test_predict_score_in_valid_range(self, sample_coordinates):
        """測試分數在有效範圍內"""
        calc = PFZCalculator()
        
        # 使用 mock 避免實際 API 調用
        with patch.object(calc, '_get_sst', return_value=26.5):
            with patch.object(calc, '_get_chla', return_value=0.35):
                with patch.object(calc, '_detect_fronts', return_value=MagicMock(front_score=70.0)):
                    with patch.object(calc, '_detect_eddies', return_value=MagicMock(eddy_score=65.0)):
                        with patch.object(calc, '_get_weather', return_value=MagicMock(operability_score=80.0)):
                            prediction = calc.predict(**sample_coordinates)
                            
                            assert 0 <= prediction.score.total_score <= 100
                            assert 0 <= prediction.score.habitat_score <= 100
                            assert 0 <= prediction.score.confidence <= 1.0
    
    def test_generic_habitat_calculation(self):
        """測試通用棲息地計算"""
        calc = PFZCalculator()
        
        # 最佳條件
        optimal_score = calc._calculate_generic_habitat(sst=27.0, chla=0.4)
        assert optimal_score > 70, "Optimal conditions should yield high score"
        
        # 極端條件
        extreme_score = calc._calculate_generic_habitat(sst=35.0, chla=0.01)
        assert extreme_score < 50, "Extreme conditions should yield low score"
        
        # 無數據
        no_data_score = calc._calculate_generic_habitat(sst=None, chla=None)
        assert no_data_score == 50, "No data should yield neutral score"


class TestPFZPrediction:
    """PFZPrediction 測試"""
    
    def test_prediction_to_dict(self):
        """測試轉換為字典"""
        score = PFZScore(
            total_score=75.0,
            habitat_score=80.0,
            front_score=70.0,
            eddy_score=65.0,
            weather_score=85.0,
            trend_score=75.0,
            confidence=0.72,
            recommendation="測試"
        )
        prediction = PFZPrediction(
            lat=22.5,
            lon=121.0,
            time=datetime.now(),
            score=score,
            target_species="yellowfin_tuna"
        )
        
        result = prediction.to_dict()
        
        assert "lat" in result
        assert "lon" in result
        assert "score" in result
        assert result["lat"] == 22.5
        assert result["lon"] == 121.0


class TestEdgeCases:
    """邊界條件測試"""
    
    def test_extreme_latitude(self):
        """測試極端緯度"""
        calc = PFZCalculator()
        
        # 北極點附近
        with patch.object(calc, '_get_sst', return_value=2.0):
            with patch.object(calc, '_get_chla', return_value=0.1):
                with patch.object(calc, '_detect_fronts', return_value=MagicMock(front_score=30.0)):
                    with patch.object(calc, '_detect_eddies', return_value=MagicMock(eddy_score=20.0)):
                        with patch.object(calc, '_get_weather', return_value=MagicMock(operability_score=40.0)):
                            prediction = calc.predict(lat=85.0, lon=0.0)
                            assert prediction.score.total_score < 50
    
    def test_date_line_crossing(self):
        """測試跨越日期變更線"""
        calc = PFZCalculator()
        
        with patch.object(calc, '_get_sst', return_value=26.0):
            with patch.object(calc, '_get_chla', return_value=0.3):
                with patch.object(calc, '_detect_fronts', return_value=MagicMock(front_score=60.0)):
                    with patch.object(calc, '_detect_eddies', return_value=MagicMock(eddy_score=55.0)):
                        with patch.object(calc, '_get_weather', return_value=MagicMock(operability_score=70.0)):
                            # 179.9° E
                            prediction1 = calc.predict(lat=0.0, lon=179.9)
                            # 179.9° W
                            prediction2 = calc.predict(lat=0.0, lon=-179.9)
                            
                            # 兩個預測都應該成功
                            assert prediction1.score is not None
                            assert prediction2.score is not None
    
    def test_invalid_species_handling(self):
        """測試無效魚種處理"""
        calc = PFZCalculator(target_species="invalid_species")
        
        # 應該不會拋出異常，而是使用通用設定
        with patch.object(calc, '_get_sst', return_value=26.0):
            with patch.object(calc, '_get_chla', return_value=0.3):
                with patch.object(calc, '_detect_fronts', return_value=MagicMock(front_score=60.0)):
                    with patch.object(calc, '_detect_eddies', return_value=MagicMock(eddy_score=55.0)):
                        with patch.object(calc, '_get_weather', return_value=MagicMock(operability_score=70.0)):
                            prediction = calc.predict(lat=22.5, lon=121.0)
                            assert prediction is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
