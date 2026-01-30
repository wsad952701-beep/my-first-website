"""
Line Messaging API 通知模組

提供 Line 推播通知功能，包括：
- 純文字訊息
- Flex Message 卡片
- 漁場報告
- 警報通知
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import json

import requests

try:
    from ..config import get_settings
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LineMessage:
    """Line 訊息基類"""
    type: str
    content: Dict[str, Any]


class LineNotifier:
    """
    Line 通知器
    
    透過 Line Messaging API 發送推播通知。
    
    Attributes:
        channel_token: Line Channel Access Token
        api_base: Line API 基礎 URL
    
    Example:
        >>> notifier = LineNotifier(channel_token="YOUR_TOKEN")
        >>> notifier.send_text("U1234567890", "Hello from PFZ System!")
    """
    
    API_BASE = "https://api.line.me/v2/bot"
    
    def __init__(
        self,
        channel_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化 Line 通知器
        
        Args:
            channel_token: Line Channel Access Token
            timeout: 請求超時時間
        """
        settings = get_settings()
        
        self.channel_token = channel_token or settings.api.line_channel_token
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.channel_token}",
            "Content-Type": "application/json"
        })
    
    @property
    def is_configured(self) -> bool:
        """是否已配置"""
        return bool(self.channel_token)
    
    def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        發送 API 請求
        
        Args:
            endpoint: API 端點
            payload: 請求內容
            
        Returns:
            API 響應
        """
        if not self.is_configured:
            logger.warning("Line channel token not configured")
            return {"error": "Not configured"}
        
        url = f"{self.API_BASE}/{endpoint}"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json() if response.text else {}
            
        except requests.RequestException as e:
            logger.error(f"Line API request failed: {e}")
            return {"error": str(e)}
    
    def send_text(
        self,
        user_id: str,
        text: str
    ) -> Dict[str, Any]:
        """
        發送純文字訊息
        
        Args:
            user_id: 接收者 Line User ID
            text: 訊息內容
            
        Returns:
            API 響應
        """
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
        
        return self._make_request("message/push", payload)
    
    def send_test_message(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        發送測試訊息
        
        Args:
            user_id: 接收者 User ID，若未指定則使用環境變數 LINE_USER_ID
            
        Returns:
            API 響應
        """
        settings = get_settings()
        target_user = user_id or settings.api.line_user_id
        
        if not target_user:
            return {"error": "No user_id provided and LINE_USER_ID not configured"}
        
        if not self.is_configured:
            return {"error": "LINE_CHANNEL_TOKEN not configured"}
        
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        test_message = f"""🎣 PFZ System 測試訊息

✅ Line 通知功能正常運作！

⏰ 發送時間: {now}
📍 系統版本: 1.0.0

祝您漁獲滿載！🐟"""
        
        return self.send_text(target_user, test_message)
    
    def send_flex(
        self,
        user_id: str,
        flex_content: Dict[str, Any],
        alt_text: str = "PFZ 漁場報告"
    ) -> Dict[str, Any]:
        """
        發送 Flex Message
        
        Args:
            user_id: 接收者 User ID
            flex_content: Flex Message 內容
            alt_text: 替代文字
            
        Returns:
            API 響應
        """
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "flex",
                    "altText": alt_text,
                    "contents": flex_content
                }
            ]
        }
        
        return self._make_request("message/push", payload)
    
    def send_pfz_report(
        self,
        user_id: str,
        location_name: str,
        pfz_score: float,
        level: str,
        scores: Dict[str, float],
        recommendation: str,
        sst: Optional[float] = None,
        weather: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        發送 PFZ 漁場報告
        
        Args:
            user_id: 接收者 User ID
            location_name: 位置名稱
            pfz_score: PFZ 總分
            level: 等級
            scores: 分項分數
            recommendation: 建議
            sst: 海表溫度
            weather: 天氣狀況
            
        Returns:
            API 響應
        """
        # 決定顏色
        if pfz_score >= 80:
            color = "#28a745"
            emoji = "🎯"
        elif pfz_score >= 60:
            color = "#17a2b8"
            emoji = "✅"
        elif pfz_score >= 40:
            color = "#ffc107"
            emoji = "⚠️"
        else:
            color = "#dc3545"
            emoji = "❌"
        
        # 構建 Flex Message
        flex_content = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{emoji} PFZ 漁場報告",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#ffffff"
                    }
                ],
                "backgroundColor": color,
                "paddingAll": "15px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": location_name,
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{pfz_score:.0f}",
                                "size": "4xl",
                                "weight": "bold",
                                "color": color
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "分",
                                        "size": "sm"
                                    },
                                    {
                                        "type": "text",
                                        "text": level,
                                        "size": "lg",
                                        "weight": "bold"
                                    }
                                ],
                                "justifyContent": "center"
                            }
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_score_row("🌡️ 棲息地", scores.get("habitat", 0)),
                            self._create_score_row("🌊 鋒面", scores.get("front", 0)),
                            self._create_score_row("🔄 渦旋", scores.get("eddy", 0)),
                            self._create_score_row("☁️ 氣象", scores.get("weather", 0)),
                        ],
                        "margin": "lg",
                        "spacing": "sm"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": recommendation,
                        "wrap": True,
                        "size": "sm",
                        "color": "#666666"
                    },
                    {
                        "type": "text",
                        "text": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "size": "xs",
                        "color": "#999999",
                        "align": "end",
                        "margin": "md"
                    }
                ]
            }
        }
        
        # 添加環境數據
        if sst is not None or weather:
            env_contents = []
            if sst is not None:
                env_contents.append({
                    "type": "text",
                    "text": f"🌡️ SST: {sst:.1f}°C",
                    "size": "sm"
                })
            if weather:
                env_contents.append({
                    "type": "text",
                    "text": f"☁️ {weather}",
                    "size": "sm"
                })
            
            # 插入到 body
            flex_content["body"]["contents"].insert(1, {
                "type": "box",
                "layout": "horizontal",
                "contents": env_contents,
                "margin": "sm",
                "spacing": "lg"
            })
        
        return self.send_flex(user_id, flex_content, f"PFZ 報告: {location_name}")
    
    def _create_score_row(
        self,
        label: str,
        score: float
    ) -> Dict[str, Any]:
        """創建分數行"""
        return {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "sm",
                    "flex": 3
                },
                {
                    "type": "text",
                    "text": f"{score:.0f}",
                    "size": "sm",
                    "align": "end",
                    "flex": 1
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "backgroundColor": self._get_score_color(score),
                            "width": f"{score}%",
                            "height": "6px",
                            "cornerRadius": "3px"
                        }
                    ],
                    "backgroundColor": "#E0E0E0",
                    "cornerRadius": "3px",
                    "flex": 5,
                    "margin": "md"
                }
            ]
        }
    
    def _get_score_color(self, score: float) -> str:
        """根據分數返回顏色"""
        if score >= 80:
            return "#28a745"
        elif score >= 60:
            return "#17a2b8"
        elif score >= 40:
            return "#ffc107"
        else:
            return "#dc3545"
    
    def send_typhoon_alert(
        self,
        user_id: str,
        typhoon_name: str,
        risk_level: str,
        distance_km: float,
        recommendation: str
    ) -> Dict[str, Any]:
        """
        發送颱風警報
        
        Args:
            user_id: 接收者 User ID
            typhoon_name: 颱風名稱
            risk_level: 風險等級
            distance_km: 距離 (km)
            recommendation: 建議
            
        Returns:
            API 響應
        """
        # 風險等級配色
        level_colors = {
            "extreme": "#dc3545",
            "high": "#fd7e14",
            "moderate": "#ffc107",
            "low": "#28a745"
        }
        
        color = level_colors.get(risk_level, "#6c757d")
        
        flex_content = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ 颱風警報",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff"
                    }
                ],
                "backgroundColor": color,
                "paddingAll": "12px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": typhoon_name,
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "text",
                        "text": f"距離: {distance_km:.0f} km",
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": f"風險等級: {risk_level.upper()}",
                        "color": color,
                        "weight": "bold",
                        "margin": "sm"
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "text",
                        "text": recommendation,
                        "wrap": True,
                        "margin": "lg",
                        "size": "sm"
                    }
                ]
            }
        }
        
        return self.send_flex(user_id, flex_content, f"颱風警報: {typhoon_name}")
    
    def broadcast(
        self,
        message: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        廣播訊息給所有追蹤者
        
        Args:
            message: 文字訊息或 Flex Message 內容
            
        Returns:
            API 響應
        """
        if isinstance(message, str):
            messages = [{"type": "text", "text": message}]
        else:
            messages = [{"type": "flex", "altText": "PFZ 通知", "contents": message}]
        
        payload = {"messages": messages}
        
        return self._make_request("message/broadcast", payload)


def send_notification(
    user_id: str,
    message: str,
    channel_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    便捷函數：發送通知
    
    Args:
        user_id: 接收者 User ID
        message: 訊息內容
        channel_token: Line Channel Token
        
    Returns:
        API 響應
    """
    notifier = LineNotifier(channel_token=channel_token)
    return notifier.send_text(user_id, message)
