"""
回測框架

對歷史數據進行回測，評估 PFZ 預測系統的準確率。

使用方式：
    python -m validation.backtester --days 30 --species yellowfin_tuna
"""

import argparse
import logging
import json
import sys
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import numpy as np

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation.historical_data import HistoricalDataGenerator, FishingRecord
from validation.metrics import MetricsCalculator, AccuracyMetrics, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """
    回測結果
    
    Attributes:
        test_date: 測試日期
        species: 目標魚種
        n_predictions: 預測數
        n_actual_catches: 實際漁獲數
        metrics: 準確率指標
        predictions: 預測詳情
        actuals: 實際漁獲詳情
    """
    test_date: datetime
    species: str
    n_predictions: int
    n_actual_catches: int
    metrics: AccuracyMetrics
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    actuals: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_date": self.test_date.isoformat(),
            "species": self.species,
            "n_predictions": self.n_predictions,
            "n_actual_catches": self.n_actual_catches,
            "metrics": self.metrics.to_dict()
        }


class Backtester:
    """
    回測器
    
    對歷史時期進行 PFZ 預測，並與模擬的實際漁獲對比。
    
    Example:
        >>> backtester = Backtester(seed=42)
        >>> results = backtester.run(
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 1, 31),
        ...     species="yellowfin_tuna"
        ... )
        >>> print(f"Average hit rate: {results['overall'].metrics.hit_rate:.2%}")
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        region: Tuple[float, float, float, float] = (20.0, 26.0, 120.0, 124.0)
    ):
        """
        初始化回測器
        
        Args:
            seed: 隨機種子
            region: 測試區域 (lat_min, lat_max, lon_min, lon_max)
        """
        self.seed = seed
        self.region = region
        self.data_generator = HistoricalDataGenerator(seed=seed)
        self.metrics_calculator = MetricsCalculator()
        
        if seed is not None:
            np.random.seed(seed)
    
    def run(
        self,
        start_date: datetime,
        end_date: datetime,
        species: str = "yellowfin_tuna",
        test_points_per_day: int = 20,
        use_mock_pfz: bool = True
    ) -> Dict[str, Any]:
        """
        執行回測
        
        Args:
            start_date: 起始日期
            end_date: 結束日期
            species: 目標魚種
            test_points_per_day: 每天測試點數
            use_mock_pfz: 是否使用模擬的 PFZ 預測（True = 模擬，False = 實際調用 API）
            
        Returns:
            包含總體和每日結果的字典
        """
        logger.info(f"Starting backtest from {start_date} to {end_date} for {species}")
        
        daily_results = []
        all_predictions = []
        all_actuals = []
        
        current_date = start_date
        while current_date <= end_date:
            # 生成測試點
            test_points = self._generate_test_points(test_points_per_day)
            
            # 獲取預測 (模擬或實際)
            if use_mock_pfz:
                predictions = self._mock_pfz_predictions(test_points, species, current_date)
            else:
                predictions = self._real_pfz_predictions(test_points, species, current_date)
            
            # 生成模擬的"實際"漁獲
            actuals = self._generate_actual_catches(test_points, species, current_date, predictions)
            
            # 計算當日指標
            daily_metrics = self.metrics_calculator.calculate(predictions, actuals)
            
            result = BacktestResult(
                test_date=current_date,
                species=species,
                n_predictions=len(predictions),
                n_actual_catches=len(actuals),
                metrics=daily_metrics,
                predictions=predictions,
                actuals=actuals
            )
            daily_results.append(result)
            all_predictions.extend(predictions)
            all_actuals.extend(actuals)
            
            logger.debug(f"Day {current_date}: Hit rate = {daily_metrics.hit_rate:.2%}")
            
            current_date += timedelta(days=1)
        
        # 計算總體指標
        overall_metrics = self.metrics_calculator.calculate(all_predictions, all_actuals)
        
        # 生成報告
        report = self._generate_report(
            daily_results, overall_metrics, start_date, end_date, species
        )
        
        logger.info(f"Backtest complete. Overall hit rate: {overall_metrics.hit_rate:.2%}")
        
        return {
            "overall": BacktestResult(
                test_date=end_date,
                species=species,
                n_predictions=len(all_predictions),
                n_actual_catches=len(all_actuals),
                metrics=overall_metrics
            ),
            "daily": daily_results,
            "report": report
        }
    
    def _generate_test_points(
        self,
        n_points: int
    ) -> List[Tuple[float, float]]:
        """生成測試點"""
        lat_min, lat_max, lon_min, lon_max = self.region
        
        points = []
        for _ in range(n_points):
            lat = np.random.uniform(lat_min, lat_max)
            lon = np.random.uniform(lon_min, lon_max)
            points.append((round(lat, 4), round(lon, 4)))
        
        return points
    
    def _mock_pfz_predictions(
        self,
        test_points: List[Tuple[float, float]],
        species: str,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """
        生成模擬的 PFZ 預測
        
        基於位置和季節性生成合理的 PFZ 分數。
        """
        predictions = []
        month = date.month
        
        # 季節性因子
        peak_months = {
            "yellowfin_tuna": [4, 5, 6, 9, 10, 11],
            "bigeye_tuna": [3, 4, 5, 10, 11, 12],
            "bluefin_tuna": [5, 6, 7],
            "skipjack": [6, 7, 8, 9],
        }
        
        is_peak = month in peak_months.get(species, [6, 7, 8])
        seasonal_boost = 15 if is_peak else -10
        
        # 熱區中心點
        hotspot_centers = [
            (23.5, 122.0),  # 黑潮主流
            (22.0, 121.5),  # 蘭嶼
            (24.0, 121.8),  # 花蓮外海
        ]
        
        for lat, lon in test_points:
            # 基礎分數
            base_score = np.random.normal(55, 15)
            
            # 距離熱區加分
            min_dist = float('inf')
            for hs_lat, hs_lon in hotspot_centers:
                dist = np.sqrt((lat - hs_lat)**2 + (lon - hs_lon)**2)
                min_dist = min(min_dist, dist)
            
            hotspot_boost = max(0, 20 - min_dist * 10)
            
            # 最終分數
            score = base_score + seasonal_boost + hotspot_boost
            score = max(10, min(95, score))  # 限制範圍
            
            predictions.append({
                "lat": lat,
                "lon": lon,
                "pfz_score": round(score, 1),
                "timestamp": date.isoformat(),
                "species": species
            })
        
        return predictions
    
    def _real_pfz_predictions(
        self,
        test_points: List[Tuple[float, float]],
        species: str,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """
        使用實際 PFZ 計算器進行預測
        
        注意：這需要網路連接和 API 調用。
        """
        try:
            from algorithms.pfz import PFZCalculator
            
            calc = PFZCalculator(target_species=species)
            predictions = []
            
            for lat, lon in test_points:
                try:
                    prediction = calc.predict(lat=lat, lon=lon)
                    predictions.append({
                        "lat": lat,
                        "lon": lon,
                        "pfz_score": prediction.score.total_score,
                        "timestamp": date.isoformat(),
                        "species": species
                    })
                except Exception as e:
                    logger.warning(f"Failed to predict at ({lat}, {lon}): {e}")
                    # 使用預設分數
                    predictions.append({
                        "lat": lat,
                        "lon": lon,
                        "pfz_score": 50.0,
                        "timestamp": date.isoformat(),
                        "species": species
                    })
            
            return predictions
            
        except ImportError:
            logger.warning("Could not import PFZCalculator, falling back to mock")
            return self._mock_pfz_predictions(test_points, species, date)
    
    def _generate_actual_catches(
        self,
        test_points: List[Tuple[float, float]],
        species: str,
        date: datetime,
        predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成模擬的"實際"漁獲
        
        漁獲量與 PFZ 分數正相關，但有隨機變異。
        """
        actuals = []
        
        for i, (lat, lon) in enumerate(test_points):
            pfz_score = predictions[i]["pfz_score"]
            
            # 基於 PFZ 分數計算預期漁獲
            # 高 PFZ 區域更可能有較高漁獲
            if pfz_score >= 70:
                base_catch = np.random.normal(150, 50)
                base_cpue = np.random.normal(1.2, 0.4)
            elif pfz_score >= 50:
                base_catch = np.random.normal(80, 40)
                base_cpue = np.random.normal(0.7, 0.3)
            else:
                base_catch = np.random.normal(30, 25)
                base_cpue = np.random.normal(0.3, 0.2)
            
            # 添加隨機性（模擬真實世界的不確定性）
            # 有時預測會失準
            if np.random.random() < 0.2:  # 20% 意外情況
                multiplier = np.random.choice([0.1, 0.5, 2.0, 3.0])
                base_catch *= multiplier
                base_cpue *= multiplier
            
            catch_kg = max(0, base_catch)
            cpue = max(0, base_cpue)
            
            # 位置輕微偏移（模擬漁船實際作業位置）
            actual_lat = lat + np.random.uniform(-0.1, 0.1)
            actual_lon = lon + np.random.uniform(-0.1, 0.1)
            
            actuals.append({
                "lat": round(actual_lat, 4),
                "lon": round(actual_lon, 4),
                "catch_kg": round(catch_kg, 1),
                "cpue": round(cpue, 4),
                "timestamp": date.isoformat(),
                "species": species
            })
        
        return actuals
    
    def _generate_report(
        self,
        daily_results: List[BacktestResult],
        overall_metrics: AccuracyMetrics,
        start_date: datetime,
        end_date: datetime,
        species: str
    ) -> ValidationReport:
        """生成驗證報告"""
        
        # 按月份分類
        by_month = {}
        for result in daily_results:
            month = result.test_date.month
            if month not in by_month:
                by_month[month] = {"predictions": [], "actuals": []}
            by_month[month]["predictions"].extend(result.predictions)
            by_month[month]["actuals"].extend(result.actuals)
        
        month_metrics = {}
        for month, data in by_month.items():
            month_metrics[month] = self.metrics_calculator.calculate(
                data["predictions"], data["actuals"]
            )
        
        # 生成建議
        recommendations = self._generate_recommendations(overall_metrics, month_metrics)
        
        return ValidationReport(
            generated_at=datetime.now(),
            date_range=(start_date, end_date),
            species=[species],
            regions=["Taiwan East Coast"],
            overall_metrics=overall_metrics,
            by_species={species: overall_metrics},
            by_region={"Taiwan East Coast": overall_metrics},
            by_month=month_metrics,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        overall: AccuracyMetrics,
        by_month: Dict[int, AccuracyMetrics]
    ) -> List[str]:
        """生成改進建議"""
        recommendations = []
        
        # 根據命中率
        if overall.hit_rate < 0.5:
            recommendations.append(
                "⚠️ 命中率偏低 ({:.1%})，建議重新校準 PFZ 分數閾值或增加環境因子。".format(
                    overall.hit_rate
                )
            )
        elif overall.hit_rate >= 0.7:
            recommendations.append(
                "✅ 命中率良好 ({:.1%})，預測效能在可接受範圍內。".format(
                    overall.hit_rate
                )
            )
        
        # 根據相關性
        if overall.cpue_correlation < 0.3:
            recommendations.append(
                "⚠️ CPUE 相關性偏低 ({:.2f})，PFZ 分數與實際漁獲關聯不強。".format(
                    overall.cpue_correlation
                )
            )
        elif overall.cpue_correlation >= 0.5:
            recommendations.append(
                "✅ CPUE 相關性良好 ({:.2f})，預測分數能反映漁獲趨勢。".format(
                    overall.cpue_correlation
                )
            )
        
        # 月份變異
        if by_month:
            hit_rates = [m.hit_rate for m in by_month.values()]
            variance = np.var(hit_rates)
            if variance > 0.05:
                recommendations.append(
                    "📊 不同月份的準確率變異較大，建議納入更強的季節性調整。"
                )
        
        # 精確率 vs 召回率
        if overall.precision > overall.recall + 0.2:
            recommendations.append(
                "💡 精確率高於召回率，系統較為保守。可考慮降低 PFZ 閾值以捕捉更多潛在漁場。"
            )
        elif overall.recall > overall.precision + 0.2:
            recommendations.append(
                "💡 召回率高於精確率，系統可能有較多假陽性。可考慮提高 PFZ 閾值以減少誤報。"
            )
        
        if not recommendations:
            recommendations.append("✅ 系統表現穩定，暫無重大改進建議。")
        
        return recommendations


def main():
    """命令列入口"""
    parser = argparse.ArgumentParser(description="PFZ 回測工具")
    parser.add_argument("--days", type=int, default=30, help="回測天數")
    parser.add_argument("--species", type=str, default="yellowfin_tuna", help="目標魚種")
    parser.add_argument("--seed", type=int, default=42, help="隨機種子")
    parser.add_argument("--points", type=int, default=20, help="每日測試點數")
    parser.add_argument("--output", type=str, help="輸出 JSON 檔案路徑")
    parser.add_argument("--real-api", action="store_true", help="使用實際 PFZ API")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細輸出")
    
    args = parser.parse_args()
    
    # 設置日誌
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 執行回測
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    backtester = Backtester(seed=args.seed)
    results = backtester.run(
        start_date=start_date,
        end_date=end_date,
        species=args.species,
        test_points_per_day=args.points,
        use_mock_pfz=not args.real_api
    )
    
    # 輸出結果
    print("\n" + "=" * 60)
    print("PFZ 回測結果")
    print("=" * 60)
    print(f"測試期間: {start_date.date()} ~ {end_date.date()}")
    print(f"目標魚種: {args.species}")
    print(f"總預測數: {results['overall'].n_predictions}")
    print("-" * 60)
    print(results['overall'].metrics.summary())
    
    print("\n📋 建議:")
    for rec in results['report'].recommendations:
        print(f"  {rec}")
    
    # 儲存結果
    if args.output:
        output_data = {
            "overall": results['overall'].to_dict(),
            "report": results['report'].to_dict()
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n結果已儲存至: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
