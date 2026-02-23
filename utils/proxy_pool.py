"""
Управление пулом прокси
Ротация и проверка работоспособности прокси
"""

from typing import List, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ProxyPool:
    """Пул прокси с ротацией"""

    def __init__(self, proxies: List[str] = None):
        """
        Args:
            proxies: Список прокси в формате http://host:port
        """
        self.proxies = proxies or settings.PROXY_LIST
        self.current_index = 0
        self.failed_proxies = set()

        if self.proxies:
            logger.info(f"✓ Инициализирован пул из {len(self.proxies)} прокси")
        else:
            logger.info("ℹ️ Прокси не настроены, работа без прокси")

    def get_next(self) -> Optional[str]:
        """
        Получить следующий прокси из пула

        Returns:
            URL прокси или None
        """
        if not self.proxies:
            return None

        # Пропускаем неработающие прокси
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

            if proxy not in self.failed_proxies:
                return proxy

            attempts += 1

        # Если все прокси в failed - сбрасываем список и пробуем снова
        if self.failed_proxies:
            logger.warning("⚠️ Все прокси помечены как неработающие, сброс списка")
            self.failed_proxies.clear()
            return self.proxies[0]

        return None

    def mark_failed(self, proxy: str):
        """Пометить прокси как неработающий"""
        if proxy and proxy not in self.failed_proxies:
            self.failed_proxies.add(proxy)
            logger.warning(f"⚠️ Прокси помечен как неработающий: {proxy}")

    def mark_success(self, proxy: str):
        """Пометить прокси как работающий"""
        if proxy in self.failed_proxies:
            self.failed_proxies.remove(proxy)
            logger.info(f"✓ Прокси восстановлен: {proxy}")
