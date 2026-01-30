#!/usr/bin/env python3
"""
PFZ System - 主程式入口

提供命令列介面與 API 服務。

Usage:
    # 單點 PFZ 查詢
    python main.py pfz --lat 22.5 --lon 121.0 --species yellowfin_tuna
    
    # 氣象預報
    python main.py weather --lat 22.5 --lon 121.0 --days 3
    
    # 作業適宜度
    python main.py operability --lat 22.5 --lon 121.0 --vessel longline
    
    # 颱風檢查
    python main.py typhoon --lat 22.5 --lon 121.0
    
    # ROI 分析
    python main.py roi --origin 22.6,120.3 --dest 24.0,122.0 --pfz-score 75
    
    # 發送報告
    python main.py report --lat 22.5 --lon 121.0 --user-id U1234567890
"""

import argparse
import json
import logging
import sys
import os
from datetime import datetime
from typing import Optional

# Fix Windows console encoding for Unicode/emoji output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure the parent directory is in sys.path for proper imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from config import get_settings, configure_logging
from algorithms import PFZCalculator, calculate_pfz
from weather import (
    GlobalWeatherFetcher,
    get_weather_forecast,
    get_operability_forecast,
    TyphoonMonitor
)
from business import ROICalculator, calculate_roi
from notification import LineNotifier

logger = logging.getLogger(__name__)


def cmd_pfz(args):
    """PFZ 預測命令"""
    print(f"\n🎯 PFZ 漁場預測")
    print(f"   位置: ({args.lat}, {args.lon})")
    print(f"   目標魚種: {args.species or '通用'}")
    print("-" * 40)
    
    try:
        calc = PFZCalculator(
            target_species=args.species,
            vessel_type=args.vessel
        )
        prediction = calc.predict(args.lat, args.lon, args.days)
        
        score = prediction.score
        
        print(f"\n📊 PFZ 總分: {score.total_score:.1f} ({score.level})")
        print(f"\n分項分數:")
        print(f"   🌡️ 棲息地: {score.habitat_score:.1f}")
        print(f"   🌊 鋒面:   {score.front_score:.1f}")
        print(f"   🔄 渦旋:   {score.eddy_score:.1f}")
        print(f"   ☁️ 氣象:   {score.weather_score:.1f}")
        print(f"   📈 趨勢:   {score.trend_score:.1f}")
        print(f"\n信心度: {score.confidence:.0%}")
        print(f"\n💡 建議: {score.recommendation}")
        
        if args.json:
            print("\n" + json.dumps(prediction.to_dict(), indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"PFZ 計算失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def cmd_weather(args):
    """氣象預報命令"""
    print(f"\n☁️ 氣象預報")
    print(f"   位置: ({args.lat}, {args.lon})")
    print(f"   預報天數: {args.days}")
    print("-" * 40)
    
    try:
        forecast = get_weather_forecast(args.lat, args.lon, args.days)
        
        if forecast.empty:
            print("❌ 無法獲取氣象數據")
            return 1
        
        print(f"\n使用模型: {forecast.get('models_used', ['自動選擇'])[0] if 'models_used' in forecast.columns else '自動'}")
        
        # 顯示摘要
        print("\n📋 未來 72 小時摘要:")
        
        cols_to_show = [
            ("wind_speed_10m_mean", "風速 (m/s)"),
            ("wave_height", "波高 (m)"),
            ("temperature_2m_mean", "氣溫 (°C)"),
            ("precipitation_mean", "降水 (mm)")
        ]
        
        for col, label in cols_to_show:
            if col in forecast.columns:
                vals = forecast[col].dropna()
                if len(vals) > 0:
                    print(f"   {label}: {vals.min():.1f} - {vals.max():.1f} (平均: {vals.mean():.1f})")
        
        if args.json:
            # 輸出前 24 小時
            sample = forecast.head(24)
            print("\n" + sample.to_json(orient="records", indent=2, date_format="iso"))
            
    except Exception as e:
        logger.error(f"氣象獲取失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def cmd_operability(args):
    """作業適宜度命令"""
    print(f"\n⚙️ 作業適宜度評估")
    print(f"   位置: ({args.lat}, {args.lon})")
    print(f"   漁法: {args.vessel}")
    print("-" * 40)
    
    try:
        forecast = get_operability_forecast(
            args.lat, args.lon,
            vessel_type=args.vessel,
            forecast_days=args.days
        )
        
        if forecast.empty:
            print("❌ 無法獲取數據")
            return 1
        
        # 顯示未來幾小時
        print("\n📋 未來 24 小時作業適宜度:")
        
        for idx, row in forecast.head(24).iterrows():
            time_str = row['time'].strftime('%m/%d %H:%M') if hasattr(row['time'], 'strftime') else str(row['time'])[:16]
            score = row.get('operability_score', 0)
            level = row.get('operability_level', 'N/A')
            
            # 簡單進度條
            bar_len = int(score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            print(f"   {time_str} │{bar}│ {score:.0f} ({level})")
            
    except Exception as e:
        logger.error(f"適宜度評估失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def cmd_typhoon(args):
    """颱風檢查命令"""
    print(f"\n🌀 颱風風險檢查")
    print(f"   位置: ({args.lat}, {args.lon})")
    print("-" * 40)
    
    try:
        monitor = TyphoonMonitor()
        impact = monitor.check_typhoon_impact(args.lat, args.lon, args.radius)
        
        if impact["has_impact"]:
            print(f"\n⚠️ 發現颱風威脅!")
            print(f"   最高風險等級: {impact['max_risk_level'].upper()}")
            print(f"   影響颱風數: {impact['typhoon_count']}")
            
            for imp in impact["impacts"]:
                print(f"\n   🌀 {imp['typhoon_name']} ({imp['category']})")
                print(f"      距離: {imp['distance_km']:.0f} km")
                print(f"      風險: {imp['risk_level']}")
                if imp.get('hours_to_impact'):
                    print(f"      預計影響: {imp['hours_to_impact']:.0f} 小時後")
            
            print(f"\n💡 建議: {impact['recommendation']}")
        else:
            print("\n✅ 目前無颱風威脅")
            print(f"   {impact['recommendation']}")
            
    except Exception as e:
        logger.error(f"颱風檢查失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def cmd_roi(args):
    """ROI 分析命令"""
    origin = tuple(map(float, args.origin.split(',')))
    dest = tuple(map(float, args.dest.split(',')))
    
    print(f"\n💰 ROI 分析")
    print(f"   出發: ({origin[0]}, {origin[1]})")
    print(f"   目標: ({dest[0]}, {dest[1]})")
    print(f"   PFZ 分數: {args.pfz_score}")
    print(f"   目標魚種: {args.species}")
    print("-" * 40)
    
    try:
        result = calculate_roi(
            origin=origin,
            destination=dest,
            pfz_score=args.pfz_score,
            target_species=args.species
        )
        
        print(f"\n📊 分析結果:")
        print(f"   預期收入: ${result.expected_revenue:,.2f}")
        print(f"   總成本:   ${result.total_cost:,.2f}")
        print(f"   淨利潤:   ${result.net_profit:,.2f}")
        print(f"   ROI:      {result.roi_percentage:.1f}%")
        print(f"\n   損益平衡漁獲: {result.break_even_catch_kg:.1f} kg")
        print(f"\n💡 建議: {result.recommendation}")
        
        if args.json:
            print("\n" + json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"ROI 分析失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def cmd_report(args):
    """發送報告命令"""
    # 獲取 user_id，優先使用參數，否則使用環境變數
    settings = get_settings()
    user_id = args.user_id or settings.api.line_user_id
    
    if not user_id:
        print("❌ 未指定 User ID")
        print("   請使用 --user-id 參數或設置 LINE_USER_ID 環境變數")
        return 1
    
    print(f"\n📤 發送 PFZ 報告")
    print(f"   位置: ({args.lat}, {args.lon})")
    print(f"   User ID: {user_id}")
    print("-" * 40)
    
    try:
        # 計算 PFZ
        prediction = calculate_pfz(args.lat, args.lon, args.species)
        score = prediction.score
        
        # 發送報告
        notifier = LineNotifier()
        
        if not notifier.is_configured:
            print("❌ Line Channel Token 未配置")
            print("   請設置環境變數 LINE_CHANNEL_TOKEN")
            return 1
        
        result = notifier.send_pfz_report(
            user_id=user_id,
            location_name=f"({args.lat}, {args.lon})",
            pfz_score=score.total_score,
            level=score.level,
            scores={
                "habitat": score.habitat_score,
                "front": score.front_score,
                "eddy": score.eddy_score,
                "weather": score.weather_score
            },
            recommendation=score.recommendation
        )
        
        if "error" in result:
            print(f"❌ 發送失敗: {result['error']}")
            return 1
        
        print("✅ 報告已發送!")
        
    except Exception as e:
        logger.error(f"報告發送失敗: {e}")
        print(f"❌ 錯誤: {e}")
        return 1
    
    return 0


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="PFZ System - 潛在漁場預測系統",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細輸出")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # PFZ 命令
    pfz_parser = subparsers.add_parser("pfz", help="PFZ 漁場預測")
    pfz_parser.add_argument("--lat", type=float, required=True, help="緯度")
    pfz_parser.add_argument("--lon", type=float, required=True, help="經度")
    pfz_parser.add_argument("--species", type=str, help="目標魚種")
    pfz_parser.add_argument("--vessel", type=str, default="longline", help="漁法")
    pfz_parser.add_argument("--days", type=int, default=3, help="預報天數")
    pfz_parser.add_argument("--json", action="store_true", help="輸出 JSON")
    
    # 氣象命令
    weather_parser = subparsers.add_parser("weather", help="氣象預報")
    weather_parser.add_argument("--lat", type=float, required=True, help="緯度")
    weather_parser.add_argument("--lon", type=float, required=True, help="經度")
    weather_parser.add_argument("--days", type=int, default=3, help="預報天數")
    weather_parser.add_argument("--json", action="store_true", help="輸出 JSON")
    
    # 作業適宜度命令
    op_parser = subparsers.add_parser("operability", help="作業適宜度")
    op_parser.add_argument("--lat", type=float, required=True, help="緯度")
    op_parser.add_argument("--lon", type=float, required=True, help="經度")
    op_parser.add_argument("--vessel", type=str, default="longline", help="漁法")
    op_parser.add_argument("--days", type=int, default=3, help="預報天數")
    
    # 颱風命令
    typhoon_parser = subparsers.add_parser("typhoon", help="颱風檢查")
    typhoon_parser.add_argument("--lat", type=float, required=True, help="緯度")
    typhoon_parser.add_argument("--lon", type=float, required=True, help="經度")
    typhoon_parser.add_argument("--radius", type=float, default=300, help="警戒半徑 (nm)")
    
    # ROI 命令
    roi_parser = subparsers.add_parser("roi", help="ROI 分析")
    roi_parser.add_argument("--origin", type=str, required=True, help="出發點 (lat,lon)")
    roi_parser.add_argument("--dest", type=str, required=True, help="目標點 (lat,lon)")
    roi_parser.add_argument("--pfz-score", type=float, required=True, help="PFZ 分數")
    roi_parser.add_argument("--species", type=str, default="yellowfin_tuna", help="目標魚種")
    roi_parser.add_argument("--json", action="store_true", help="輸出 JSON")
    
    # 報告命令
    report_parser = subparsers.add_parser("report", help="發送報告")
    report_parser.add_argument("--lat", type=float, required=True, help="緯度")
    report_parser.add_argument("--lon", type=float, required=True, help="經度")
    report_parser.add_argument("--user-id", type=str, help="Line User ID (預設使用 LINE_USER_ID 環境變數)")
    report_parser.add_argument("--species", type=str, help="目標魚種")
    
    args = parser.parse_args()
    
    # 設定日誌
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if not args.command:
        parser.print_help()
        return 0
    
    # 執行命令
    commands = {
        "pfz": cmd_pfz,
        "weather": cmd_weather,
        "operability": cmd_operability,
        "typhoon": cmd_typhoon,
        "roi": cmd_roi,
        "report": cmd_report
    }
    
    if args.command in commands:
        return commands[args.command](args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
