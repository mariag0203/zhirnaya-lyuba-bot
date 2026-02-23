"""
Модуль конфигурации приложения.

Загружает переменные окружения из .env файла и предоставляет
централизованный доступ к настройкам бота, API-ключам, параметрам
мониторинга и подключения к базе данных.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Telegram Client (Telethon) for channel monitoring
TG_API_ID: int = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH: str = os.getenv("TG_API_HASH", "")
TG_PHONE: str = os.getenv("TG_PHONE", "")

# VK API
VK_TOKEN: str = os.getenv("VK_TOKEN", "")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

# Proxy
PROXY_LIST: list[str] = [
    p.strip()
    for p in os.getenv("PROXY_LIST", "").split(",")
    if p.strip()
]

# Monitoring intervals (seconds)
BASE_INTERVAL: int = int(os.getenv("BASE_INTERVAL", "60"))
ENHANCED_INTERVAL: int = int(os.getenv("ENHANCED_INTERVAL", "2"))
ENHANCED_DURATION: int = int(os.getenv("ENHANCED_DURATION", "900"))

# Target URLs
SHALOM_URL: str = "https://shalom-theatre.ru"
AFISHA_URL: str = "https://www.afisha.ru"
MOSBILET_URL: str = "https://bilet.mos.ru"
