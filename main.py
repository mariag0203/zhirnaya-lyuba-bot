"""
Точка входа: Telegram-бот + мониторинг Мосбилета
"""

import asyncio
import logging
import time
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config.settings import settings
from database import init_db, close_db
from bot import router
from bot.handlers import MONITOR
from utils.scheduler import MonitorScheduler


def setup_logging():
    """Лог в bot.log (ротация: 5 файлов по 5 МБ) и в stdout (журнал systemd). Время — московское."""
    fmt = logging.Formatter('%(asctime)s MSK - %(name)s - %(levelname)s - %(message)s')
    fmt.converter = lambda secs: time.gmtime(secs + 3 * 3600)
    file_handler = RotatingFileHandler('bot.log', maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
    # служебные сообщения aiogram о каждом апдейте не нужны
    logging.getLogger('aiogram.event').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def main():
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"✗ Ошибка конфигурации: {e}. Проверьте файл .env")
        return

    logger.info("=" * 60)
    logger.info("🎭 Запуск бота мониторинга «Жирная Люба» (Мосбилет)")
    logger.info(f"   Событие: {settings.event_url}, интервал {settings.BASE_INTERVAL} с")
    logger.info("=" * 60)

    await init_db()

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = MonitorScheduler()
    MONITOR['mosbilet'] = scheduler.add_monitors(bot=bot)
    await scheduler.start_all()
    logger.info(f"✅ Бот @{(await bot.get_me()).username} запущен")

    try:
        # aiogram сам корректно завершает polling по SIGTERM (systemctl stop/restart)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("🔄 Завершение работы...")
        await scheduler.stop_all()
        await bot.session.close()
        await close_db()
        logger.info("✅ Бот остановлен")


if __name__ == '__main__':
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
