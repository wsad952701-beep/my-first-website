"""
歷史漁獲數據生成器

由於沒有真實歷史數據，使用統計模擬生成合理的歷史漁獲記錄。
這些模擬數據用於系統驗證和回測框架開發。

注意：生產環境應使用真實漁獲數據進行驗證。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import random

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FishingRecord:
    """
    漁獲記錄
    
    Attributes:
        record_id: 記錄 ID
        timestamp: 時間戳
        lat: 緯度
        lon: 經度
        species: 魚種
        catch_kg: 漁獲量 (kg)
        cpue: 單位努力漁獲量 (kg/hook 或 kg/set)
        vessel_id: 船隻 ID
        fishing_method: 漁法
        effort: 作業努力量
        sst: 當時海表溫度 (°C)
        metadata: 其他元數據
    """
    record_id: str
    timestamp: datetime
    lat: float
    lon: float
    species: str
    catch_kg: float
    cpue: float
    vessel_id: str
    fishing_method: str
    effort: float
    sst: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "lat": self.lat,
            "lon": self.lon,
            "species": self.species,
            "catch_kg": self.catch_kg,
            "cpue": self.cpue,
            "vessel_id": self.vessel_id,
            "fishing_method": self.fishing_method,
            "effort": self.effort,
            "sst": self.sst,
            "metadata": self.metadata
        }


# 魚種棲息特性（用於模擬）
SPECIES_CHARACTERISTICS = {
    "yellowfin_tuna": {
        "preferred_sst": (24, 28),
        "base_cpue": 0.8,  # kg/hook
        "cpue_std": 0.4,
        "seasonal_peak": [4, 5, 6, 9, 10, 11],  # 旺季月份
        "depth_range": (50, 250)
    },
    "bigeye_tuna": {
        "preferred_sst": (17, 22),
        "base_cpue": 0.5,
        "cpue_std": 0.3,
        "seasonal_peak": [3, 4, 5, 10, 11, 12],
        "depth_range": (100, 400)
    },
    "bluefin_tuna": {
        "preferred_sst": (18, 24),
        "base_cpue": 0.2,
        "cpue_std": 0.15,
        "seasonal_peak": [5, 6, 7],
        "depth_range": (50, 200)
    },
    "skipjack": {
        "preferred_sst": (26, 30),
        "base_cpue": 2.0,
        "cpue_std": 1.0,
        "seasonal_peak": [6, 7, 8, 9],
        "depth_range": (0, 100)
    },
    "albacore": {
        "preferred_sst": (15, 21),
        "base_cpue": 0.6,
        "cpue_std": 0.35,
        "seasonal_peak": [7, 8, 9, 10],
        "depth_range": (100, 300)
    },
    "swordfish": {
        "preferred_sst": (18, 22),
        "base_cpue": 0.3,
        "cpue_std": 0.2,
        "seasonal_peak": [8, 9, 10, 11],
        "depth_range": (200, 600)
    },
    "mahi_mahi": {
        "preferred_sst": (25, 29),
        "base_cpue": 1.2,
        "cpue_std": 0.6,
        "seasonal_peak": [5, 6, 7, 8, 9],
        "depth_range": (0, 50)
    }
}


# 漁場熱區（用於模擬）
FISHING_HOTSPOTS = [
    {"name": "台灣東部黑潮區", "center": (23.5, 122.0), "radius": 1.5, "weight": 1.0},
    {"name": "蘭嶼海域", "center": (22.0, 121.5), "radius": 1.0, "weight": 0.9},
    {"name": "綠島海域", "center": (22.7, 121.5), "radius": 0.8, "weight": 0.85},
    {"name": "台東外海", "center": (22.8, 121.2), "radius": 1.0, "weight": 0.8},
    {"name": "花蓮外海", "center": (24.0, 121.8), "radius": 1.2, "weight": 0.75},
    {"name": "西太平洋熱帶", "center": (8.0, 140.0), "radius": 5.0, "weight": 0.7},
    {"name": "中太平洋漁場", "center": (0.0, 160.0), "radius": 8.0, "weight": 0.65},
]


class HistoricalDataGenerator:
    """
    歷史漁獲數據生成器
    
    基於統計模型和漁業知識生成模擬的歷史漁獲記錄。
    
    Example:
        >>> generator = HistoricalDataGenerator(seed=42)
        >>> records = generator.generate(
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 12, 31),
        ...     n_vessels=10,
        ...     species=["yellowfin_tuna", "bigeye_tuna"]
        ... )
        >>> print(f"Generated {len(records)} records")
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        初始化生成器
        
        Args:
            seed: 隨機種子（用於可重複性）
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.vessel_ids = [f"FV-{i:03d}" for i in range(1, 101)]
        self.record_counter = 0
    
    def generate(
        self,
        start_date: datetime,
        end_date: datetime,
        n_vessels: int = 10,
        species: Optional[List[str]] = None,
        region: Optional[Tuple[float, float, float, float]] = None,
        avg_trips_per_month: int = 2
    ) -> List[FishingRecord]:
        """
        生成歷史漁獲記錄
        
        Args:
            start_date: 起始日期
            end_date: 結束日期
            n_vessels: 船隻數量
            species: 目標魚種列表
            region: 區域邊界 (lat_min, lat_max, lon_min, lon_max)
            avg_trips_per_month: 每月平均航次數
            
        Returns:
            List[FishingRecord]
        """
        if species is None:
            species = list(SPECIES_CHARACTERISTICS.keys())
        
        if region is None:
            region = (20.0, 26.0, 120.0, 124.0)  # 台灣東部海域預設區域
        
        records = []
        vessels = random.sample(self.vessel_ids, min(n_vessels, len(self.vessel_ids)))
        
        current_date = start_date
        while current_date <= end_date:
            month = current_date.month
            
            # 每月生成航次
            n_trips = max(1, int(np.random.poisson(avg_trips_per_month)))
            
            for _ in range(n_trips):
                vessel = random.choice(vessels)
                target_species = random.choice(species)
                
                # 生成航次記錄
                trip_records = self._generate_trip(
                    vessel_id=vessel,
                    trip_date=current_date,
                    species=target_species,
                    region=region
                )
                records.extend(trip_records)
            
            # 下個月
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1)
        
        logger.info(f"Generated {len(records)} fishing records from {start_date} to {end_date}")
        return records
    
    def _generate_trip(
        self,
        vessel_id: str,
        trip_date: datetime,
        species: str,
        region: Tuple[float, float, float, float]
    ) -> List[FishingRecord]:
        """生成單次航次記錄"""
        records = []
        
        # 航次天數 (3-10 天)
        trip_days = random.randint(3, 10)
        
        # 選擇作業位置（偏向熱區）
        base_lat, base_lon = self._select_fishing_location(region)
        
        # 獲取魚種特性
        char = SPECIES_CHARACTERISTICS.get(species, SPECIES_CHARACTERISTICS["yellowfin_tuna"])
        
        # 季節性調整
        is_peak_season = trip_date.month in char["seasonal_peak"]
        seasonal_factor = 1.5 if is_peak_season else 0.7
        
        # 模擬 SST（基於偏好範圍）
        sst_min, sst_max = char["preferred_sst"]
        sst = random.uniform(sst_min - 2, sst_max + 2)
        
        # 溫度適宜度
        if sst_min <= sst <= sst_max:
            temp_factor = 1.0
        else:
            temp_deviation = min(abs(sst - sst_min), abs(sst - sst_max))
            temp_factor = max(0.2, 1.0 - temp_deviation * 0.1)
        
        # 每天作業
        for day in range(trip_days):
            current_datetime = trip_date + timedelta(days=day)
            
            # 隨機漂移位置
            lat = base_lat + random.uniform(-0.5, 0.5)
            lon = base_lon + random.uniform(-0.5, 0.5)
            
            # 確保在區域內
            lat = max(region[0], min(region[1], lat))
            lon = max(region[2], min(region[3], lon))
            
            # 作業努力量（延繩釣的鉤數）
            effort = random.randint(800, 2000)
            
            # 計算 CPUE
            base_cpue = char["base_cpue"]
            cpue_std = char["cpue_std"]
            
            # 應用各種因子
            adjusted_cpue = base_cpue * seasonal_factor * temp_factor
            
            # 添加隨機變異
            cpue = max(0, np.random.normal(adjusted_cpue, cpue_std))
            
            # 計算漁獲量
            catch_kg = cpue * effort
            
            # 某些天可能沒有漁獲
            if random.random() < 0.1:  # 10% 機率無漁獲
                catch_kg = 0
                cpue = 0
            
            self.record_counter += 1
            record = FishingRecord(
                record_id=f"REC-{self.record_counter:08d}",
                timestamp=current_datetime,
                lat=round(lat, 4),
                lon=round(lon, 4),
                species=species,
                catch_kg=round(catch_kg, 1),
                cpue=round(cpue, 4),
                vessel_id=vessel_id,
                fishing_method="longline",
                effort=effort,
                sst=round(sst, 1),
                metadata={
                    "trip_day": day + 1,
                    "trip_days": trip_days,
                    "seasonal_factor": round(seasonal_factor, 2),
                    "temp_factor": round(temp_factor, 2)
                }
            )
            records.append(record)
        
        return records
    
    def _select_fishing_location(
        self,
        region: Tuple[float, float, float, float]
    ) -> Tuple[float, float]:
        """選擇作業位置，偏向已知熱區"""
        lat_min, lat_max, lon_min, lon_max = region
        
        # 篩選區域內的熱區
        valid_hotspots = [
            hs for hs in FISHING_HOTSPOTS
            if lat_min <= hs["center"][0] <= lat_max
            and lon_min <= hs["center"][1] <= lon_max
        ]
        
        if valid_hotspots and random.random() < 0.7:  # 70% 機率選擇熱區
            # 加權隨機選擇熱區
            weights = [hs["weight"] for hs in valid_hotspots]
            total = sum(weights)
            weights = [w / total for w in weights]
            
            hotspot = random.choices(valid_hotspots, weights=weights, k=1)[0]
            
            # 在熱區範圍內隨機選擇
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(0, hotspot["radius"])
            
            lat = hotspot["center"][0] + distance * np.sin(angle)
            lon = hotspot["center"][1] + distance * np.cos(angle)
        else:
            # 隨機位置
            lat = random.uniform(lat_min, lat_max)
            lon = random.uniform(lon_min, lon_max)
        
        return lat, lon
    
    def generate_for_validation(
        self,
        test_locations: List[Tuple[float, float]],
        dates: List[datetime],
        species: str = "yellowfin_tuna"
    ) -> Dict[Tuple[float, float, datetime], FishingRecord]:
        """
        為驗證生成特定位置和日期的漁獲記錄
        
        這用於驗證預測與"實際"漁獲的對比。
        
        Args:
            test_locations: 測試位置列表
            dates: 測試日期列表
            species: 目標魚種
            
        Returns:
            以 (lat, lon, date) 為鍵的記錄字典
        """
        result = {}
        
        for lat, lon in test_locations:
            for date in dates:
                records = self._generate_trip(
                    vessel_id="VALIDATION",
                    trip_date=date,
                    species=species,
                    region=(lat - 0.5, lat + 0.5, lon - 0.5, lon + 0.5)
                )
                
                if records:
                    # 取第一筆作為代表
                    result[(lat, lon, date)] = records[0]
        
        return result


def save_records_to_csv(records: List[FishingRecord], filepath: str):
    """將記錄儲存為 CSV"""
    import csv
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'record_id', 'timestamp', 'lat', 'lon', 'species',
            'catch_kg', 'cpue', 'vessel_id', 'fishing_method', 'effort', 'sst'
        ])
        writer.writeheader()
        
        for record in records:
            row = record.to_dict()
            del row['metadata']
            writer.writerow(row)
    
    logger.info(f"Saved {len(records)} records to {filepath}")


if __name__ == "__main__":
    # 示範用
    generator = HistoricalDataGenerator(seed=42)
    records = generator.generate(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        n_vessels=10,
        species=["yellowfin_tuna", "bigeye_tuna"]
    )
    print(f"Generated {len(records)} records")
    print(f"First record: {records[0].to_dict()}")
