"""
Монитор портала bilet.mos.ru.

Отслеживает появление льготных и обычных билетов на мероприятия
московских театров через портал городских услуг bilet.mos.ru.
"""

import logging
from typing import Any

from bs4 import BeautifulSoup

from monitors.base_monitor import BaseMonitor
from config.settings import MOSBILET_URL

logger = logging.getLogger(__name__)


class MosbiletMonitor(BaseMonitor):
    """Монитор bilet.mos.ru."""

    name = "mosbilet"

    def __init__(self, event_url: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.event_url = event_url or MOSBILET_URL

    async def check(self) -> dict[str, Any] | None:
        """Проверяет наличие билетов на bilet.mos.ru."""
        assert self._session is not None
        async with self._session.get(self.event_url, timeout=10) as resp:
            html = await resp.text()

        soup = BeautifulSoup(html, "lxml")
        # TODO: адаптировать селекторы под реальную структуру bilet.mos.ru
        ticket_link = soup.select_one(".ticket-card__buy, .event-buy-btn, [href*='buy']")
        if ticket_link:
            return {"source": self.name, "url": self.event_url}
        return None
