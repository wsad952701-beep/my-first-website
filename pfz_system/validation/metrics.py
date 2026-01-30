"""
準確率評估指標

提供 PFZ 預測準確率的評估指標：
- 命中率 (Hit Rate)
- CPUE 相關係數
- 空間誤差
- 分類準確率
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    """
    準確率指標
    
    Attributes:
        hit_rate: 命中率 (0-1)
        cpue_correlation: CPUE 相關係數 (-1 to 1)
        spatial_error_km: 平均空間誤差 (km)
        classification_accuracy: 分類準確率 (0-1)
        precision: 精確率 (高 PFZ 區域的命中率)
        recall: 召回率 (實際漁獲中被預測到的比例)
        f1_score: F1 分數
        confusion_matrix: 混淆矩陣
        sample_size: 樣本數
    """
    hit_rate: float
    cpue_correlation: float
    spatial_error_km: float
    classification_accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Dict[str, Dict[str, int]]
    sample_size: int
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hit_rate": self.hit_rate,
            "cpue_correlation": self.cpue_correlation,
            "spatial_error_km": self.spatial_error_km,
            "classification_accuracy": self.classification_accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "confusion_matrix": self.confusion_matrix,
            "sample_size": self.sample_size,
            "details": self.details
        }
    
    def summary(self) -> str:
        """生成摘要報告"""
        lines = [
            "=" * 50,
            "PFZ 準確率評估報告",
            "=" * 50,
            f"樣本數: {self.sample_size}",
            "-" * 50,
            f"命中率: {self.hit_rate:.2%}",
            f"CPUE 相關係數: {self.cpue_correlation:.3f}",
            f"平均空間誤差: {self.spatial_error_km:.1f} km",
            f"分類準確率: {self.classification_accuracy:.2%}",
            "-" * 50,
            f"精確率: {self.precision:.2%}",
            f"召回率: {self.recall:.2%}",
            f"F1 分數: {self.f1_score:.3f}",
            "=" * 50
        ]
        return "\n".join(lines)


@dataclass
class ValidationReport:
    """
    驗證報告
    
    包含完整的驗證結果和分析。
    """
    generated_at: datetime
    date_range: Tuple[datetime, datetime]
    species: List[str]
    regions: List[str]
    overall_metrics: AccuracyMetrics
    by_species: Dict[str, AccuracyMetrics]
    by_region: Dict[str, AccuracyMetrics]
    by_month: Dict[int, AccuracyMetrics]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "date_range": [d.isoformat() for d in self.date_range],
            "species": self.species,
            "regions": self.regions,
            "overall_metrics": self.overall_metrics.to_dict(),
            "by_species": {k: v.to_dict() for k, v in self.by_species.items()},
            "by_region": {k: v.to_dict() for k, v in self.by_region.items()},
            "by_month": {k: v.to_dict() for k, v in self.by_month.items()},
            "recommendations": self.recommendations
        }


class MetricsCalculator:
    """
    指標計算器
    
    計算 PFZ 預測與實際漁獲之間的各種準確率指標。
    """
    
    # PFZ 分數分類閾值
    THRESHOLDS = {
        "high": 70,      # >= 70 為高
        "medium": 50,    # 50-70 為中
        "low": 0         # < 50 為低
    }
    
    # 漁獲量分類閾值 (kg/天)
    CATCH_THRESHOLDS = {
        "high": 100,     # >= 100 kg
        "medium": 30,    # 30-100 kg
        "low": 0         # < 30 kg
    }
    
    def __init__(
        self,
        pfz_thresholds: Optional[Dict[str, float]] = None,
        catch_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        初始化計算器
        
        Args:
            pfz_thresholds: 自定義 PFZ 分類閾值
            catch_thresholds: 自定義漁獲分類閾值
        """
        self.pfz_thresholds = pfz_thresholds or self.THRESHOLDS
        self.catch_thresholds = catch_thresholds or self.CATCH_THRESHOLDS
    
    def calculate(
        self,
        predictions: List[Dict[str, Any]],
        actuals: List[Dict[str, Any]]
    ) -> AccuracyMetrics:
        """
        計算準確率指標
        
        Args:
            predictions: 預測結果列表
                每個項目需包含: lat, lon, pfz_score, timestamp
            actuals: 實際漁獲列表
                每個項目需包含: lat, lon, catch_kg, cpue, timestamp
                
        Returns:
            AccuracyMetrics
        """
        if len(predictions) != len(actuals):
            logger.warning(
                f"Prediction count ({len(predictions)}) != actual count ({len(actuals)})"
            )
        
        n = min(len(predictions), len(actuals))
        if n == 0:
            return self._empty_metrics()
        
        # 提取數據
        pfz_scores = np.array([p["pfz_score"] for p in predictions[:n]])
        catch_values = np.array([a["catch_kg"] for a in actuals[:n]])
        cpue_values = np.array([a.get("cpue", 0) for a in actuals[:n]])
        
        # 分類
        pfz_classes = self._classify_pfz(pfz_scores)
        catch_classes = self._classify_catch(catch_values)
        
        # 計算各指標
        hit_rate = self._calculate_hit_rate(pfz_classes, catch_classes)
        cpue_corr = self._calculate_cpue_correlation(pfz_scores, cpue_values)
        spatial_error = self._calculate_spatial_error(predictions[:n], actuals[:n])
        class_acc = self._calculate_classification_accuracy(pfz_classes, catch_classes)
        precision, recall, f1 = self._calculate_prf(pfz_classes, catch_classes)
        confusion = self._calculate_confusion_matrix(pfz_classes, catch_classes)
        
        return AccuracyMetrics(
            hit_rate=hit_rate,
            cpue_correlation=cpue_corr,
            spatial_error_km=spatial_error,
            classification_accuracy=class_acc,
            precision=precision,
            recall=recall,
            f1_score=f1,
            confusion_matrix=confusion,
            sample_size=n,
            details={
                "pfz_score_mean": float(np.mean(pfz_scores)),
                "pfz_score_std": float(np.std(pfz_scores)),
                "catch_mean": float(np.mean(catch_values)),
                "catch_std": float(np.std(catch_values))
            }
        )
    
    def _classify_pfz(self, scores: np.ndarray) -> np.ndarray:
        """將 PFZ 分數分類"""
        classes = np.empty(len(scores), dtype=object)
        classes[scores >= self.pfz_thresholds["high"]] = "high"
        classes[(scores >= self.pfz_thresholds["medium"]) & 
                (scores < self.pfz_thresholds["high"])] = "medium"
        classes[scores < self.pfz_thresholds["medium"]] = "low"
        return classes
    
    def _classify_catch(self, catches: np.ndarray) -> np.ndarray:
        """將漁獲量分類"""
        classes = np.empty(len(catches), dtype=object)
        classes[catches >= self.catch_thresholds["high"]] = "high"
        classes[(catches >= self.catch_thresholds["medium"]) & 
                (catches < self.catch_thresholds["high"])] = "medium"
        classes[catches < self.catch_thresholds["medium"]] = "low"
        return classes
    
    def _calculate_hit_rate(
        self,
        pfz_classes: np.ndarray,
        catch_classes: np.ndarray
    ) -> float:
        """
        計算命中率
        
        定義：預測為 high 且實際也是 high 的比例
        """
        high_predictions = pfz_classes == "high"
        if not np.any(high_predictions):
            return 0.0
        
        hits = (pfz_classes == "high") & (catch_classes == "high")
        return float(np.sum(hits) / np.sum(high_predictions))
    
    def _calculate_cpue_correlation(
        self,
        pfz_scores: np.ndarray,
        cpue_values: np.ndarray
    ) -> float:
        """
        計算 PFZ 分數與 CPUE 的相關係數
        """
        # 移除 NaN 和無效值
        valid = ~(np.isnan(pfz_scores) | np.isnan(cpue_values))
        if np.sum(valid) < 3:
            return 0.0
        
        corr, _ = stats.pearsonr(pfz_scores[valid], cpue_values[valid])
        return float(corr) if not np.isnan(corr) else 0.0
    
    def _calculate_spatial_error(
        self,
        predictions: List[Dict[str, Any]],
        actuals: List[Dict[str, Any]]
    ) -> float:
        """
        計算平均空間誤差 (km)
        
        這是預測熱點與實際漁獲位置的平均距離。
        """
        errors = []
        for pred, actual in zip(predictions, actuals):
            lat1, lon1 = pred["lat"], pred["lon"]
            lat2, lon2 = actual["lat"], actual["lon"]
            
            # Haversine 公式計算距離 (km)
            R = 6371  # 地球半徑
            lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            
            a = np.sin(dlat/2)**2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            
            distance = R * c
            errors.append(distance)
        
        return float(np.mean(errors)) if errors else 0.0
    
    def _calculate_classification_accuracy(
        self,
        pfz_classes: np.ndarray,
        catch_classes: np.ndarray
    ) -> float:
        """計算分類準確率"""
        return float(np.mean(pfz_classes == catch_classes))
    
    def _calculate_prf(
        self,
        pfz_classes: np.ndarray,
        catch_classes: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        計算精確率、召回率、F1 分數
        
        以 "high" 為正類。
        """
        # True Positive: 預測 high 且實際 high
        tp = np.sum((pfz_classes == "high") & (catch_classes == "high"))
        # False Positive: 預測 high 但實際不是 high
        fp = np.sum((pfz_classes == "high") & (catch_classes != "high"))
        # False Negative: 預測不是 high 但實際是 high
        fn = np.sum((pfz_classes != "high") & (catch_classes == "high"))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return float(precision), float(recall), float(f1)
    
    def _calculate_confusion_matrix(
        self,
        pfz_classes: np.ndarray,
        catch_classes: np.ndarray
    ) -> Dict[str, Dict[str, int]]:
        """計算混淆矩陣"""
        classes = ["high", "medium", "low"]
        matrix = {pred: {actual: 0 for actual in classes} for pred in classes}
        
        for pred, actual in zip(pfz_classes, catch_classes):
            if pred in classes and actual in classes:
                matrix[pred][actual] += 1
        
        return matrix
    
    def _empty_metrics(self) -> AccuracyMetrics:
        """返回空的指標"""
        return AccuracyMetrics(
            hit_rate=0.0,
            cpue_correlation=0.0,
            spatial_error_km=0.0,
            classification_accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            confusion_matrix={
                "high": {"high": 0, "medium": 0, "low": 0},
                "medium": {"high": 0, "medium": 0, "low": 0},
                "low": {"high": 0, "medium": 0, "low": 0}
            },
            sample_size=0
        )


def evaluate_predictions(
    predictions: List[Dict[str, Any]],
    actuals: List[Dict[str, Any]]
) -> AccuracyMetrics:
    """
    便捷函數：評估預測準確率
    
    Args:
        predictions: 預測結果
        actuals: 實際漁獲
        
    Returns:
        AccuracyMetrics
    """
    calculator = MetricsCalculator()
    return calculator.calculate(predictions, actuals)


if __name__ == "__main__":
    # 示範用
    import random
    
    # 生成模擬數據
    n = 100
    predictions = [
        {"lat": 22.5 + random.uniform(-1, 1), 
         "lon": 121.0 + random.uniform(-1, 1),
         "pfz_score": random.uniform(30, 90),
         "timestamp": "2024-06-15"}
        for _ in range(n)
    ]
    
    actuals = [
        {"lat": p["lat"] + random.uniform(-0.2, 0.2),
         "lon": p["lon"] + random.uniform(-0.2, 0.2),
         "catch_kg": p["pfz_score"] * random.uniform(0.5, 2.0),
         "cpue": p["pfz_score"] * random.uniform(0.01, 0.03),
         "timestamp": "2024-06-15"}
        for p in predictions
    ]
    
    metrics = evaluate_predictions(predictions, actuals)
    print(metrics.summary())
