"""
Монитор Telegram-канала театра.

Использует Telethon для подключения к Telegram как пользователь
и отслеживания новых сообщений в целевом канале. При обнаружении
сообщений о билетах инициирует уведомление подписчиков.
"""

import logging
from typing import Any

from telethon import TelegramClient, events

from config.settings import TG_API_ID, TG_API_HASH, TG_PHONE

logger = logging.getLogger(__name__)


class TelegramChannelMonitor:
    """Монитор Telegram-канала через Telethon."""

    name = "telegram_channel"

    TICKET_KEYWORDS = ("билет", "ticket", "купить", "продажа", "доступны")

    def __init__(self, channel: str) -> None:
        """
        Args:
            channel: Username или ссылка на Telegram-канал.
        """
        self.channel = channel
        self.client = TelegramClient("session_monitor", TG_API_ID, TG_API_HASH)
        self._callback: Any = None

    def set_callback(self, callback: Any) -> None:
        """Устанавливает callback, вызываемый при обнаружении билетов."""
        self._callback = callback

    async def start(self) -> None:
        """Запускает прослушивание канала."""
        await self.client.start(phone=TG_PHONE)

        @self.client.on(events.NewMessage(chats=self.channel))
        async def handler(event: events.NewMessage.Event) -> None:
            text = (event.message.text or "").lower()
            if any(kw in text for kw in self.TICKET_KEYWORDS):
                logger.info("[%s] Обнаружено сообщение о билетах", self.name)
                if self._callback:
                    await self._callback({"source": self.name, "text": event.message.text})

        await self.client.run_until_disconnected()
