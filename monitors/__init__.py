"""
Monitors package
Мониторы для различных источников билетов
"""

from monitors.base_monitor import BaseMonitor
from monitors.shalom_site import ShalomSiteMonitor
from monitors.afisha import AfishaMonitor
from monitors.mosbilet import MosbiletMonitor
from monitors.telegram_channel import TelegramChannelMonitor
from monitors.vk_group import VKGroupMonitor

__all__ = [
    'BaseMonitor',
    'ShalomSiteMonitor',
    'AfishaMonitor',
    'MosbiletMonitor',
    'TelegramChannelMonitor',
    'VKGroupMonitor'
]
