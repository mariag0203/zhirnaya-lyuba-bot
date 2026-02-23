"""
Базовый класс для всех мониторов источников билетов.

Определяет общий интерфейс и вспомогательную логику, которую
наследуют конкретные мониторы: управление интервалами опроса,
ротация прокси, обработка ошибок и фиксация изменений состояния.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiohttp

from config.settings import BASE_INTERVAL, ENHANCED_INTERVAL, ENHANCED_DURATION
from utils.proxy_pool import ProxyPool

logger = logging.getLogger(__name__)


class BaseMonitor(ABC):
    """Абстрактный базовый класс монитора."""

    name: str = "base"

    def __init__(self, proxy_pool: ProxyPool | None = None) -> None:
        self.proxy_pool = proxy_pool
        self._enhanced_until: float = 0.0
        self._session: aiohttp.ClientSession | None = None

    @abstractmethod
    async def check(self) -> dict[str, Any] | None:
        """
        Выполняет одну проверку источника.

        Returns:
            Словарь с данными о билетах или None, если билетов нет.
        """

    async def run(self) -> None:
        """Запускает бесконечный цикл мониторинга с адаптивным интервалом."""
        async with aiohttp.ClientSession() as session:
            self._session = session
            while True:
                try:
                    result = await self.check()
                    if result:
                        logger.info("[%s] Билеты найдены: %s", self.name, result)
                        self._activate_enhanced_mode()
                except Exception as exc:
                    logger.error("[%s] Ошибка проверки: %s", self.name, exc)
                await asyncio.sleep(self._current_interval())

    def _current_interval(self) -> int:
        import time
        if time.time() < self._enhanced_until:
            return ENHANCED_INTERVAL
        return BASE_INTERVAL

    def _activate_enhanced_mode(self) -> None:
        import time
        self._enhanced_until = time.time() + ENHANCED_DURATION
        logger.info("[%s] Активирован усиленный режим мониторинга", self.name)
