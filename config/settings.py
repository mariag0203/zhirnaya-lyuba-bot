"""
Настройки бота: читаются из .env
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    # Telegram
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_CHAT_ID: int = _int('ADMIN_CHAT_ID', 0)

    # База
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///bot.db')

    # Интервал опроса. Нижняя граница 60 с зашита в коде: чаще сайт не опрашиваем,
    # что бы ни стояло в .env.
    MIN_INTERVAL: int = 60
    BASE_INTERVAL: int = max(MIN_INTERVAL, _int('BASE_INTERVAL', 90))

    # Мосбилет: ID события (страница https://bilet.mos.ru/event/<ID>/)
    MOSBILET_EVENT_ID: int = _int('MOSBILET_EVENT_ID', 381336257)
    MOSBILET_BASE_URL: str = 'https://bilet.mos.ru'
    # Билетная система, которую Мосбилет встраивает в страницу события (расписание и места)
    TICKETS_BASE_URL: str = 'https://tickets-external.mos.ru'

    # Не повторять уведомление о местах на один и тот же показ чаще, чем раз в N минут.
    # 26.09 места «мигали» каждые 5–15 минут, и бот прислал 20 одинаковых сообщений.
    # 0 — уведомлять о каждом переходе «0 мест → есть места».
    NOTIFY_COOLDOWN_MIN: int = max(0, _int('NOTIFY_COOLDOWN_MIN', 10))

    # Сколько проверок подряд без найденных показов считать признаком смены вёрстки/API
    PARSE_ALERT_AFTER: int = max(1, _int('PARSE_ALERT_AFTER', 5))

    # Час (по Москве), когда администратор получает ежедневное «я работаю»; -1 — выключить
    HEARTBEAT_HOUR: int = _int('HEARTBEAT_HOUR', 10)

    @property
    def event_url(self) -> str:
        return f"{self.MOSBILET_BASE_URL}/event/{self.MOSBILET_EVENT_ID}/"

    @classmethod
    def validate(cls) -> bool:
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан в .env")
        if not cls.ADMIN_CHAT_ID:
            raise ValueError("ADMIN_CHAT_ID не задан в .env")
        return True


settings = Settings()
