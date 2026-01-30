# PFZ System - 潛在漁場預測系統

🎯 **Potential Fishing Zone (PFZ) Prediction System**

整合多源海洋環境數據與氣象預報，提供精準漁場預測與作業建議。

## ✨ 功能特色

- 🌡️ **海洋數據整合** - SST、Chl-a、SSH 衛星遙測數據
- ☁️ **多國氣象模型** - GFS、ECMWF、JMA 等 7 國全球模型
- 🌊 **熱鋒面檢測** - 基於 SST 梯度的鋒面識別
- 🔄 **渦旋追蹤** - 氣旋/反氣旋渦旋檢測
- ⚙️ **作業適宜度** - 各漁法的氣象條件評估
- 🌀 **颱風監測** - 路徑追蹤與風險評估
- 💰 **ROI 分析** - 燃油成本與預期收益計算
- 📱 **Line 通知** - Flex Message 漁場報告推播

## 📁 專案結構

```
pfz_system/
├── config/                 # 系統配置
│   ├── settings.py        # 全局設定
│   ├── regions.py         # 漁場區域定義
│   └── species.py         # 魚種棲息特性
├── data/
│   └── fetchers/          # 數據獲取器
│       ├── base.py        # 基礎類與快取
│       ├── sst.py         # 海表溫度
│       ├── chla.py        # 葉綠素 a
│       └── ssh.py         # 海表高度
├── weather/               # 氣象模組
│   ├── openmeteo.py       # Open-Meteo API 封裝
│   ├── global_models.py   # 多國模型整合
│   ├── operability.py     # 作業適宜度
│   └── typhoon.py         # 颱風監測
├── algorithms/            # 預測算法
│   ├── fronts.py          # 熱鋒面檢測
│   ├── eddies.py          # 渦旋檢測
│   └── pfz.py             # PFZ 核心算法
├── business/              # 商業分析
│   └── roi.py             # ROI 計算
├── notification/          # 通知服務
│   └── line.py            # Line Messaging API
├── main.py                # 主程式入口
├── requirements.txt       # Python 依賴
├── .env.example           # 環境變數範例
├── Dockerfile             # Docker 映像
└── docker-compose.yml     # Docker Compose
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd pfz_system
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入 API Keys
```

### 3. 執行

```bash
# PFZ 漁場預測
python main.py pfz --lat 22.5 --lon 121.0 --species yellowfin_tuna

# 氣象預報
python main.py weather --lat 22.5 --lon 121.0 --days 3

# 作業適宜度
python main.py operability --lat 22.5 --lon 121.0 --vessel longline

# 颱風檢查
python main.py typhoon --lat 22.5 --lon 121.0

# ROI 分析
python main.py roi --origin 22.6,120.3 --dest 24.0,122.0 --pfz-score 75
```

## 🐳 Docker 部署

```bash
# 建構映像
docker-compose build

# 執行服務
docker-compose up -d
```

## 📊 API 使用範例

```python
from pfz_system import PFZCalculator, get_weather_forecast

# PFZ 預測
calc = PFZCalculator(target_species="yellowfin_tuna")
prediction = calc.predict(lat=22.5, lon=121.0)
print(f"PFZ Score: {prediction.score.total_score}")
print(f"建議: {prediction.score.recommendation}")

# 氣象預報
forecast = get_weather_forecast(lat=22.5, lon=121.0, days=3)
print(forecast.head())
```

## 🎯 支援魚種

| 魚種 | ID | 最佳溫度 |
|-----|-----|---------|
| 太平洋黑鮪 | bluefin_tuna | 18-24°C |
| 黃鰭鮪 | yellowfin_tuna | 24-28°C |
| 大目鮪 | bigeye_tuna | 17-22°C |
| 正鰹 | skipjack | 26-30°C |
| 長鰭鮪 | albacore | 15-21°C |
| 劍旗魚 | swordfish | 18-22°C |
| 鬼頭刀 | mahi_mahi | 25-29°C |

## 🌏 支援漁場

- 台灣東部海域
- 台灣海峽
- 西太平洋亞熱帶/熱帶漁場
- 中西太平洋赤道漁場
- 印度洋西部漁場

## 📡 數據來源

- **SST**: NOAA CoastWatch MUR SST (1km)
- **Chl-a**: MODIS Aqua/VIIRS (4km)
- **SSH**: AVISO/NESDIS
- **氣象**: Open-Meteo (GFS, ECMWF, JMA, ICON, GEM, Météo-France, UKMO)
- **海洋**: Open-Meteo Marine (波浪、涌浪、海流)

## 📄 License

MIT License

## 🤝 Contributing

歡迎提交 Issue 和 Pull Request！
