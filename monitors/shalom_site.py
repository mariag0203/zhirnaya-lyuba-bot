"""
Монитор официального сайта Театра «Шалом».

Периодически проверяет страницу спектакля на наличие доступных
билетов, парсит HTML с помощью BeautifulSoup и возвращает данные
о сеансах при их появлении.
"""

import logging
from typing import Any

from bs4 import BeautifulSoup

from monitors.base_monitor import BaseMonitor
from config.settings import SHALOM_URL

logger = logging.getLogger(__name__)


class ShalomSiteMonitor(BaseMonitor):
    """Монитор сайта shalom-theatre.ru."""

    name = "shalom_site"

    def __init__(self, target_url: str = SHALOM_URL, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.target_url = target_url

    async def check(self) -> dict[str, Any] | None:
        """Проверяет наличие билетов на сайте театра."""
        assert self._session is not None
        async with self._session.get(self.target_url, timeout=10) as resp:
            html = await resp.text()

        soup = BeautifulSoup(html, "lxml")
        # TODO: адаптировать селекторы под реальную структуру сайта
        ticket_block = soup.select_one(".ticket-buy-button, .buy-btn, [data-buy]")
        if ticket_block:
            return {"source": self.name, "url": self.target_url, "element": ticket_block.text.strip()}
        return None
