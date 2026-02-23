"""
Монитор Telegram-канала театра "Шалом"
Отслеживает новые посты в канале @shalomteatr
"""

from monitors.base_monitor import BaseMonitor
from typing import List, Dict, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class TelegramChannelMonitor(BaseMonitor):
    """Монитор Telegram-канала"""

    def __init__(self):
        super().__init__(source_name='telegram')
        self.channel = settings.TG_CHANNEL
        self.client = None  # Telethon client будет инициализирован позже
        self.last_message_id = 0

    async def initialize(self):
        """Инициализация монитора"""
        await super().initialize()

        # Проверяем наличие учетных данных
        if not settings.TG_API_ID or not settings.TG_API_HASH:
            logger.warning(f"⚠️ {self.source_name}: TG_API_ID или TG_API_HASH не установлены")
            logger.warning(f"   Монитор Telegram-канала будет отключен")
            return

        # TODO: Инициализация Telethon клиента
        # from telethon import TelegramClient
        # self.client = TelegramClient('session', settings.TG_API_ID, settings.TG_API_HASH)
        # await self.client.start(phone=settings.TG_PHONE)

        logger.info(f"✓ {self.source_name}: инициализация завершена (заглушка)")

    async def check_source(self) -> List[Dict[str, Any]]:
        """
        Проверка новых постов в канале

        Returns:
            Список найденных анонсов
        """
        # Заглушка - реальная реализация требует Telethon
        if not settings.TG_API_ID or not settings.TG_API_HASH:
            return []

        announcements = []

        # TODO: Реальная реализация с Telethon
        # async for message in self.client.iter_messages(self.channel, limit=10):
        #     if message.id <= self.last_message_id:
        #         break
        #
        #     text = message.text or ""
        #
        #     # Проверяем ключевые слова
        #     has_required = any(kw.lower() in text.lower()
        #                       for kw in settings.KEYWORDS_REQUIRED)
        #     has_sale = any(kw.lower() in text.lower()
        #                   for kw in settings.KEYWORDS_SALE)
        #
        #     if has_required and has_sale:
        #         announcements.append({
        #             'source': self.source_name,
        #             'text': text[:500],
        #             'url': f'https://t.me/{self.channel}/{message.id}',
        #             'date': message.date
        #         })
        #
        #     self.last_message_id = max(self.last_message_id, message.id)

        logger.debug(f"{self.source_name}: проверка завершена (заглушка)")
        return announcements
