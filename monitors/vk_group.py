"""
Монитор группы ВКонтакте.

Периодически опрашивает стену VK-группы театра через VK API
на предмет новых записей, содержащих информацию о билетах.
"""

import logging
from typing import Any

import vk_api

from monitors.base_monitor import BaseMonitor
from config.settings import VK_TOKEN

logger = logging.getLogger(__name__)


class VKGroupMonitor(BaseMonitor):
    """Монитор VK-группы через vk-api."""

    name = "vk_group"

    TICKET_KEYWORDS = ("билет", "ticket", "купить", "продажа", "доступны")

    def __init__(self, group_id: str, **kwargs: Any) -> None:
        """
        Args:
            group_id: Числовой ID или короткое имя группы ВКонтакте.
        """
        super().__init__(**kwargs)
        self.group_id = group_id
        self._vk: vk_api.vk_api.VkApiMethod | None = None

    def _get_vk(self) -> vk_api.vk_api.VkApiMethod:
        if self._vk is None:
            session = vk_api.VkApi(token=VK_TOKEN)
            self._vk = session.get_api()
        return self._vk

    async def check(self) -> dict[str, Any] | None:
        """Проверяет последние записи на стене VK-группы."""
        vk = self._get_vk()
        posts = vk.wall.get(owner_id=f"-{self.group_id}", count=5)
        for item in posts.get("items", []):
            text = (item.get("text") or "").lower()
            if any(kw in text for kw in self.TICKET_KEYWORDS):
                post_url = f"https://vk.com/wall-{self.group_id}_{item['id']}"
                logger.info("[%s] Найдена запись о билетах: %s", self.name, post_url)
                return {"source": self.name, "url": post_url, "text": item.get("text")}
        return None
