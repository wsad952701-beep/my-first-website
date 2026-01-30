"""
PFZ Notification Module

提供通知功能。
"""

try:
    from .line import (
        LineNotifier,
        LineMessage,
        send_notification
    )
except ImportError:
    from line import (
        LineNotifier,
        LineMessage,
        send_notification
    )

__all__ = [
    "LineNotifier",
    "LineMessage",
    "send_notification",
]
