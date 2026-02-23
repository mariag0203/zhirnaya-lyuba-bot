"""
Модуль управления пулом прокси-серверов.

Обеспечивает ротацию прокси при HTTP-запросах мониторов,
отслеживает работоспособность прокси и исключает нерабочие
адреса из ротации.
"""

import asyncio
import itertools
import logging
from typing import Iterator

import aiohttp

logger = logging.getLogger(__name__)


class ProxyPool:
    """Пул прокси с автоматической ротацией."""

    def __init__(self, proxies: list[str]) -> None:
        """
        Args:
            proxies: Список URL прокси в формате http://host:port.
        """
        self._all: list[str] = proxies
        self._healthy: list[str] = list(proxies)
        self._cycle: Iterator[str] = itertools.cycle(self._healthy)

    def next(self) -> str | None:
        """Возвращает следующий прокси из пула или None, если пул пуст."""
        if not self._healthy:
            return None
        return next(self._cycle)

    def mark_failed(self, proxy: str) -> None:
        """Помечает прокси как нерабочий и удаляет из ротации."""
        if proxy in self._healthy:
            self._healthy.remove(proxy)
            self._cycle = itertools.cycle(self._healthy)
            logger.warning("Прокси %s удалён из пула (%d осталось)", proxy, len(self._healthy))

    async def check_all(self, test_url: str = "https://httpbin.org/ip") -> None:
        """Проверяет все прокси и обновляет список рабочих."""
        results: list[str] = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._check_one(session, p, test_url) for p in self._all]
            checks = await asyncio.gather(*tasks, return_exceptions=True)
        for proxy, ok in zip(self._all, checks):
            if ok is True:
                results.append(proxy)
        self._healthy = results
        self._cycle = itertools.cycle(self._healthy)
        logger.info("Проверка прокси завершена: %d/%d рабочих", len(self._healthy), len(self._all))

    @staticmethod
    async def _check_one(session: aiohttp.ClientSession, proxy: str, url: str) -> bool:
        try:
            async with session.get(url, proxy=proxy, timeout=5):
                return True
        except Exception:
            return False
