"""
Точка входа приложения
Запуск Telegram-бота и системы мониторинга
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config.settings import settings
from database import init_db, close_db
from bot import router
from utils.scheduler import MonitorScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска"""

    # Проверка настроек
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"✗ Ошибка конфигурации: {e}")
        logger.error("   Проверьте файл .env и заполните обязательные параметры")
        return

    logger.info("=" * 60)
    logger.info("🎭 Запуск бота мониторинга билетов 'Жирная Люба'")
    logger.info("=" * 60)

    # Инициализация базы данных
    logger.info("📊 Инициализация базы данных...")
    await init_db()

    # Создание бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("✓ Telegram-бот инициализирован")

    # Запуск системы мониторинга
    scheduler = MonitorScheduler()
    scheduler.add_monitors()

    # Создаем задачу для мониторинга
    monitoring_task = asyncio.create_task(scheduler.start_all())

    logger.info("=" * 60)
    logger.info("✅ Система запущена и работает")
    logger.info(f"   Bot: @{(await bot.get_me()).username}")
    logger.info(f"   Мониторов: {len(scheduler.monitors)}")
    logger.info("=" * 60)

    try:
        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("⏹ Получен сигнал остановки...")
    finally:
        # Корректное завершение
        logger.info("🔄 Завершение работы...")

        # Остановка мониторинга
        await scheduler.stop_all()

        # Закрытие бота
        await bot.session.close()

        # Закрытие БД
        await close_db()

        logger.info("✅ Бот остановлен")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 До свидания!")
