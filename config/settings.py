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
    BASE_INTERVAL: int = int(os.getenv('BASE_INTERVAL', '60'))  # Обычный режим: 60 сек
    ENHANCED_INTERVAL: int = int(os.getenv('ENHANCED_INTERVAL', '2'))  # Усиленный: 2 сек
    ENHANCED_DURATION: int = int(os.getenv('ENHANCED_DURATION', '900'))  # Длительность усиленного режима: 15 мин

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

    # Proxy
    PROXY_LIST: List[str] = [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]

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
├─ Интервал (норм): {cls.BASE_INTERVAL} сек
├─ Интервал (усил): {cls.ENHANCED_INTERVAL} сек
├─ Длительность усиленного режима: {cls.ENHANCED_DURATION} сек
├─ Прокси: {'Да (' + str(len(cls.PROXY_LIST)) + ')' if cls.PROXY_LIST else 'Нет'}
└─ VK токен: {'✓' if cls.VK_TOKEN else '✗'}
        """.strip()

# Создание глобального экземпляра настроек
settings = Settings()
