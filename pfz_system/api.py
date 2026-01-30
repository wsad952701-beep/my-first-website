"""
PFZ System REST API

使用 FastAPI 提供 RESTful API 服務。

啟動方式：
    uvicorn api:app --reload --port 8000

API 文檔：
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

# 確保可以導入主模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "FastAPI is required. Install with: pip install fastapi uvicorn"
    )

from algorithms.pfz import PFZCalculator, calculate_pfz
from weather import (
    get_weather_forecast,
    get_operability_forecast,
    TyphoonMonitor
)
from business.roi import ROICalculator, calculate_roi, VesselSpecs

logger = logging.getLogger(__name__)

# ============================================
# Pydantic Models
# ============================================

class HealthResponse(BaseModel):
    """健康檢查響應"""
    status: str
    version: str
    timestamp: str


class CoordinatesRequest(BaseModel):
    """座標請求"""
    lat: float = Field(..., ge=-90, le=90, description="緯度")
    lon: float = Field(..., ge=-180, le=180, description="經度")


class PFZRequest(CoordinatesRequest):
    """PFZ 預測請求"""
    species: Optional[str] = Field(None, description="目標魚種")
    forecast_days: int = Field(3, ge=1, le=7, description="預報天數")


class PFZResponse(BaseModel):
    """PFZ 預測響應"""
    lat: float
    lon: float
    species: Optional[str]
    score: Dict[str, Any]
    timestamp: str


class WeatherRequest(CoordinatesRequest):
    """氣象預報請求"""
    days: int = Field(3, ge=1, le=16, description="預報天數")
    models: Optional[List[str]] = Field(None, description="氣象模型列表")


class WeatherResponse(BaseModel):
    """氣象預報響應"""
    lat: float
    lon: float
    forecast: List[Dict[str, Any]]
    model: str
    timestamp: str


class OperabilityRequest(CoordinatesRequest):
    """作業適宜度請求"""
    vessel_type: str = Field("longline", description="漁法類型")
    days: int = Field(3, ge=1, le=7, description="預報天數")


class OperabilityResponse(BaseModel):
    """作業適宜度響應"""
    lat: float
    lon: float
    vessel_type: str
    operability: List[Dict[str, Any]]
    timestamp: str


class TyphoonResponse(BaseModel):
    """颱風監測響應"""
    active_typhoons: List[Dict[str, Any]]
    warnings: List[str]
    timestamp: str


class ROIRequest(BaseModel):
    """ROI 計算請求"""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lon: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lon: float = Field(..., ge=-180, le=180)
    pfz_score: float = Field(..., ge=0, le=100, description="PFZ 分數")
    species: str = Field("yellowfin_tuna", description="目標魚種")
    operation_days: int = Field(5, ge=1, le=30, description="作業天數")
    fuel_price: Optional[float] = Field(None, description="燃油價格 (USD/L)")


class ROIResponse(BaseModel):
    """ROI 計算響應"""
    expected_revenue: float
    total_cost: float
    net_profit: float
    roi_percentage: float
    break_even_catch_kg: float
    is_profitable: bool
    recommendation: str
    details: Dict[str, Any]


class ErrorResponse(BaseModel):
    """錯誤響應"""
    error: str
    detail: str
    timestamp: str


# ============================================
# Application Setup
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    logger.info("PFZ API starting up...")
    yield
    logger.info("PFZ API shutting down...")


app = FastAPI(
    title="PFZ System API",
    description="""
## 潛在漁場預測系統 API

提供以下功能：
- 🎯 **PFZ 預測** - 基於多源海洋數據的漁場預測
- ☁️ **氣象預報** - 多國模型整合氣象預報
- ⚓ **作業適宜度** - 各漁法的氣象條件評估
- 🌀 **颱風監測** - 活動颱風追蹤與風險評估
- 💰 **ROI 分析** - 投資報酬率計算

### 支援魚種
- 太平洋黑鮪 (bluefin_tuna)
- 黃鰭鮪 (yellowfin_tuna)
- 大目鮪 (bigeye_tuna)
- 正鰹 (skipjack)
- 長鰭鮪 (albacore)
- 劍旗魚 (swordfish)
- 鬼頭刀 (mahi_mahi)
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Endpoints
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """API 根路徑"""
    return {
        "name": "PFZ System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """健康檢查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/v1/pfz", response_model=PFZResponse, tags=["PFZ"])
async def get_pfz_prediction(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="經度"),
    species: Optional[str] = Query(None, description="目標魚種"),
    forecast_days: int = Query(3, ge=1, le=7, description="預報天數")
):
    """
    獲取 PFZ 預測
    
    根據座標和目標魚種計算潛在漁場分數。
    """
    try:
        calculator = PFZCalculator(target_species=species)
        prediction = calculator.predict(
            lat=lat,
            lon=lon,
            forecast_days=forecast_days
        )
        
        return PFZResponse(
            lat=lat,
            lon=lon,
            species=species,
            score={
                "total_score": prediction.score.total_score,
                "habitat_score": prediction.score.habitat_score,
                "front_score": prediction.score.front_score,
                "eddy_score": prediction.score.eddy_score,
                "weather_score": prediction.score.weather_score,
                "trend_score": prediction.score.trend_score,
                "confidence": prediction.score.confidence,
                "level": prediction.score.level,
                "recommendation": prediction.score.recommendation
            },
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"PFZ prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/weather", response_model=WeatherResponse, tags=["Weather"])
async def get_weather(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="經度"),
    days: int = Query(3, ge=1, le=16, description="預報天數")
):
    """
    獲取氣象預報
    
    返回指定位置的多日氣象預報。
    """
    try:
        forecast = get_weather_forecast(lat=lat, lon=lon, days=days)
        
        # 轉換 DataFrame 為字典列表
        if hasattr(forecast, 'to_dict'):
            forecast_data = forecast.to_dict('records')
        else:
            forecast_data = [forecast] if isinstance(forecast, dict) else []
        
        return WeatherResponse(
            lat=lat,
            lon=lon,
            forecast=forecast_data,
            model="GFS",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Weather forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/operability", response_model=OperabilityResponse, tags=["Operability"])
async def get_operability(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="經度"),
    vessel_type: str = Query("longline", description="漁法類型"),
    days: int = Query(3, ge=1, le=7, description="預報天數")
):
    """
    獲取作業適宜度
    
    評估指定位置和漁法的作業條件。
    """
    try:
        operability = get_operability_forecast(
            lat=lat,
            lon=lon,
            vessel_type=vessel_type,
            days=days
        )
        
        # 轉換為字典列表
        if hasattr(operability, 'to_dict'):
            operability_data = operability.to_dict('records')
        else:
            operability_data = [operability] if isinstance(operability, dict) else []
        
        return OperabilityResponse(
            lat=lat,
            lon=lon,
            vessel_type=vessel_type,
            operability=operability_data,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Operability calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/typhoon", response_model=TyphoonResponse, tags=["Typhoon"])
async def get_typhoon_status(
    lat: Optional[float] = Query(None, ge=-90, le=90, description="監測位置緯度"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="監測位置經度")
):
    """
    獲取颱風狀態
    
    返回活動颱風列表和警報。
    """
    try:
        monitor = TyphoonMonitor()
        typhoons = monitor.get_active_typhoons()
        
        warnings = []
        if lat is not None and lon is not None:
            risk = monitor.assess_risk(lat=lat, lon=lon)
            if risk and risk.get('risk_level', 'low') != 'low':
                warnings.append(risk.get('warning', '請注意颱風動態'))
        
        # 轉換颱風資料
        typhoon_data = []
        if typhoons:
            for t in typhoons:
                typhoon_data.append(t.to_dict() if hasattr(t, 'to_dict') else t)
        
        return TyphoonResponse(
            active_typhoons=typhoon_data,
            warnings=warnings,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Typhoon monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/roi", response_model=ROIResponse, tags=["ROI"])
async def calculate_roi_analysis(request: ROIRequest):
    """
    計算 ROI 分析
    
    評估漁業作業的投資報酬率。
    """
    try:
        # 設定船舶規格和燃油價格
        fuel_price = request.fuel_price or 0.8
        calculator = ROICalculator(fuel_price_usd_per_l=fuel_price)
        
        result = calculator.calculate(
            origin=(request.origin_lat, request.origin_lon),
            destination=(request.dest_lat, request.dest_lon),
            pfz_score=request.pfz_score,
            target_species=request.species,
            operation_days=request.operation_days
        )
        
        return ROIResponse(
            expected_revenue=result.expected_revenue,
            total_cost=result.total_cost,
            net_profit=result.net_profit,
            roi_percentage=result.roi_percentage,
            break_even_catch_kg=result.break_even_catch_kg,
            is_profitable=result.is_profitable,
            recommendation=result.recommendation,
            details={
                "fuel_cost": result.fuel_cost.to_dict(),
                "expected_catches": [c.to_dict() for c in result.expected_catches],
                **result.details
            }
        )
        
    except Exception as e:
        logger.error(f"ROI calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/species", tags=["Reference"])
async def list_species():
    """列出支援的魚種"""
    from config.species import SPECIES_CONFIG
    
    species_list = []
    for species_id, config in SPECIES_CONFIG.items():
        species_list.append({
            "id": species_id,
            "name": config.get("name_zh", species_id),
            "name_en": config.get("name_en", species_id),
            "optimal_sst": config.get("optimal_sst", [20, 28])
        })
    
    return {"species": species_list}


@app.get("/api/v1/regions", tags=["Reference"])
async def list_regions():
    """列出支援的漁場區域"""
    from config.regions import REGIONS
    
    regions_list = []
    for region_id, config in REGIONS.items():
        regions_list.append({
            "id": region_id,
            "name": config.get("name", region_id),
            "bbox": config.get("bbox", [])
        })
    
    return {"regions": regions_list}


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            detail=exc.detail,
            timestamp=datetime.now().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
