"""
PFZ Algorithms Module

提供漁場預測算法。
"""

try:
    from .fronts import (
        FrontDetector,
        FrontSegment,
        FrontDetectionResult,
        detect_fronts
    )
    from .eddies import (
        EddyDetector,
        Eddy,
        EddyType,
        EddyDetectionResult,
        detect_eddies
    )
    from .pfz import (
        PFZCalculator,
        PFZScore,
        PFZPrediction,
        calculate_pfz
    )
except ImportError:
    from fronts import (
        FrontDetector,
        FrontSegment,
        FrontDetectionResult,
        detect_fronts
    )
    from eddies import (
        EddyDetector,
        Eddy,
        EddyType,
        EddyDetectionResult,
        detect_eddies
    )
    from pfz import (
        PFZCalculator,
        PFZScore,
        PFZPrediction,
        calculate_pfz
    )

__all__ = [
    # Fronts
    "FrontDetector",
    "FrontSegment",
    "FrontDetectionResult",
    "detect_fronts",
    # Eddies
    "EddyDetector",
    "Eddy",
    "EddyType",
    "EddyDetectionResult",
    "detect_eddies",
    # PFZ
    "PFZCalculator",
    "PFZScore",
    "PFZPrediction",
    "calculate_pfz",
]
