"""
Мониторы. Сейчас один — Мосбилет.
"""

from monitors.base_monitor import BaseMonitor
from monitors.mosbilet import MosbiletMonitor

__all__ = ['BaseMonitor', 'MosbiletMonitor']
