"""
Точка входа приложения.

Инициализирует бота aiogram, базу данных, планировщик задач
и запускает все мониторы параллельно с основным polling-циклом бота.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from config.settings import BOT_TOKEN, PROXY_LIST, BASE_INTERVAL
from bot.handlers import router
from database.db import init_db
from monitors.shalom_site import ShalomSiteMonitor
from monitors.afisha import AfishaMonitor
from monitors.mosbilet import MosbiletMonitor
from utils.proxy_pool import ProxyPool
from utils.scheduler import MonitorScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная корутина: запускает бота и все мониторы."""
    await init_db()
    logger.info("База данных инициализирована")

    proxy_pool = ProxyPool(PROXY_LIST) if PROXY_LIST else None

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = MonitorScheduler()
    monitors = [
        ShalomSiteMonitor(proxy_pool=proxy_pool),
        AfishaMonitor(proxy_pool=proxy_pool),
        MosbiletMonitor(proxy_pool=proxy_pool),
    ]

    for monitor in monitors:
        scheduler.add_monitor(monitor.name, monitor.check, BASE_INTERVAL)
    scheduler.start()

    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
