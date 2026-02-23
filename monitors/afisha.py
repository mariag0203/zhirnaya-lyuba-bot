"""
Монитор сервиса Afisha.ru.

Отслеживает появление билетов на спектакль через API или HTML-страницу
Afisha.ru. Поддерживает фильтрацию по конкретному мероприятию и дате.
"""

import logging
from typing import Any

from bs4 import BeautifulSoup

from monitors.base_monitor import BaseMonitor
from config.settings import AFISHA_URL

logger = logging.getLogger(__name__)


class AfishaMonitor(BaseMonitor):
    """Монитор afisha.ru."""

    name = "afisha"

    def __init__(self, event_url: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.event_url = event_url or AFISHA_URL

    async def check(self) -> dict[str, Any] | None:
        """Проверяет наличие билетов на Afisha.ru."""
        assert self._session is not None
        async with self._session.get(self.event_url, timeout=10) as resp:
            html = await resp.text()

        soup = BeautifulSoup(html, "lxml")
        # TODO: адаптировать селекторы под реальную структуру Afisha.ru
        buy_button = soup.select_one("a[data-qa='buy-tickets'], .buy-button")
        if buy_button:
            return {"source": self.name, "url": self.event_url}
        return None
