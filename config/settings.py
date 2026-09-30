"""
Конфигурация бота для мониторинга билетов на "Жирную Любу"
Загружает настройки из .env файла и предоставляет централизованный доступ к ним
"""

import os
from dotenv import load_dotenv
from typing import List, Optional

# Загрузка переменных окружения
load_dotenv()

class Settings:
    """Класс настроек приложения"""

    # Telegram Bot
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_CHAT_ID: int = int(os.getenv('ADMIN_CHAT_ID', '0'))

    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///bot.db')

    # Monitoring intervals (в секундах)
    # Нижняя граница интервала жёстко 60 сек — чаще опрашивать сайт не будем,
    # что бы ни стояло в .env. Усиленного режима больше нет.
    MIN_INTERVAL: int = 60
    BASE_INTERVAL: int = max(MIN_INTERVAL, int(os.getenv('BASE_INTERVAL', '90')))

    # Какие мониторы запускать (через запятую). По умолчанию только Мосбилет.
    ENABLED_MONITORS: List[str] = [m.strip() for m in os.getenv('ENABLED_MONITORS', 'mosbilet').split(',') if m.strip()]

    # Мосбилет: точное название спектакля и (необязательно) дополнительные ID событий
    MOSBILET_TITLE: str = os.getenv('MOSBILET_TITLE', 'Жирная Люба')
    MOSBILET_EVENT_IDS: List[str] = [i.strip() for i in os.getenv('MOSBILET_EVENT_IDS', '').split(',') if i.strip()]

    # Keywords для поиска
    KEYWORDS_REQUIRED: List[str] = os.getenv('KEYWORDS_REQUIRED', 'Жирная Люба').split(',')
    KEYWORDS_SALE: List[str] = os.getenv('KEYWORDS_SALE', 'билеты,продажа').split(',')

    # VK API
    VK_TOKEN: str = os.getenv('VK_TOKEN', '')
    VK_GROUP_ID: str = 'teatrshalom'

    # Telegram Channel
    TG_API_ID: Optional[int] = int(os.getenv('TG_API_ID', '0')) if os.getenv('TG_API_ID') else None
    TG_API_HASH: Optional[str] = os.getenv('TG_API_HASH')
    TG_PHONE: Optional[str] = os.getenv('TG_PHONE')
    TG_CHANNEL: str = 'shalomteatr'

    # Прокси не используются: запросы идут напрямую с IP сервера.
    PROXY_LIST: List[str] = []

    # URLs для мониторинга
    SHALOM_SITE_URL: str = 'https://shalom-theatre.ru/'
    SHALOM_AFISHA_URL: str = 'https://shalom-theatre.ru/#b37860'
    AFISHA_PERFORMANCE_URL: str = 'https://www.afisha.ru/performance/zhirnaya-lyuba-248781/'
    MOSBILET_BASE_URL: str = 'https://bilet.mos.ru'
    VK_GROUP_URL: str = f'https://vk.com/{VK_GROUP_ID}'

    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных настроек"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан в .env файле!")
        if not cls.ADMIN_CHAT_ID:
            raise ValueError("ADMIN_CHAT_ID не задан в .env файле!")
        return True

    @classmethod
    def get_info(cls) -> str:
        """Возвращает информацию о текущих настройках"""
        return f"""
🔧 Текущие настройки:
├─ База: {cls.DATABASE_URL}
├─ Интервал: {cls.BASE_INTERVAL} сек
└─ Мониторы: {', '.join(cls.ENABLED_MONITORS)}
        """.strip()

# Создание глобального экземпляра настроек
settings = Settings()
