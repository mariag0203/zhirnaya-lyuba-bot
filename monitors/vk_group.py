"""
Монитор VK группы театра "Шалом"
Отслеживает новые посты в группе vk.com/teatrshalom
"""

from monitors.base_monitor import BaseMonitor
from typing import List, Dict, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class VKGroupMonitor(BaseMonitor):
    """Монитор VK группы"""

    def __init__(self):
        super().__init__(source_name='vk')
        self.group_id = settings.VK_GROUP_ID
        self.last_post_id = 0

    async def initialize(self):
        """Инициализация монитора"""
        await super().initialize()

        # Проверяем наличие токена
        if not settings.VK_TOKEN:
            logger.warning(f"⚠️ {self.source_name}: VK_TOKEN не установлен")
            logger.warning(f"   Монитор VK группы будет отключен")
            return

        logger.info(f"✓ {self.source_name}: инициализация завершена (заглушка)")

    async def check_source(self) -> List[Dict[str, Any]]:
        """
        Проверка новых постов в группе

        Returns:
            Список найденных анонсов
        """
        # Заглушка - реальная реализация требует VK API
        if not settings.VK_TOKEN:
            return []

        announcements = []

        # TODO: Реальная реализация с VK API
        # import vk_api
        # vk_session = vk_api.VkApi(token=settings.VK_TOKEN)
        # vk = vk_session.get_api()
        #
        # response = vk.wall.get(domain=self.group_id, count=10)
        # posts = response['items']
        #
        # for post in posts:
        #     if post['id'] <= self.last_post_id:
        #         continue
        #
        #     text = post.get('text', '')
        #
        #     # Проверяем ключевые слова
        #     has_required = any(kw.lower() in text.lower()
        #                       for kw in settings.KEYWORDS_REQUIRED)
        #     has_sale = any(kw.lower() in text.lower()
        #                   for kw in settings.KEYWORDS_SALE)
        #
        #     if has_required and has_sale:
        #         post_url = f"https://vk.com/wall-{response['groups'][0]['id']}_{post['id']}"
        #         announcements.append({
        #             'source': self.source_name,
        #             'text': text[:500],
        #             'url': post_url,
        #             'date': post['date']
        #         })
        #
        #     self.last_post_id = max(self.last_post_id, post['id'])

        logger.debug(f"{self.source_name}: проверка завершена (заглушка)")
        return announcements
