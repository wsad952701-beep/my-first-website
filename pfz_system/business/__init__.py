"""
PFZ Business Module

提供商業分析功能。
"""

try:
    from .roi import (
        ROICalculator,
        ROIResult,
        FuelCost,
        ExpectedCatch,
        VesselSpecs,
        MARKET_PRICES,
        calculate_roi
    )
except ImportError:
    from roi import (
        ROICalculator,
        ROIResult,
        FuelCost,
        ExpectedCatch,
        VesselSpecs,
        MARKET_PRICES,
        calculate_roi
    )

__all__ = [
    "ROICalculator",
    "ROIResult",
    "FuelCost",
    "ExpectedCatch",
    "VesselSpecs",
    "MARKET_PRICES",
    "calculate_roi",
]
