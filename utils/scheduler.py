"""
Планировщик задач для мониторинга
Управление запуском и остановкой мониторов
"""

import asyncio
from typing import List
from monitors import (
    ShalomSiteMonitor,
    AfishaMonitor,
    MosbiletMonitor,
    TelegramChannelMonitor,
    VKGroupMonitor
)
import logging

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """Планировщик мониторов"""

    def __init__(self):
        self.monitors = []
        self.tasks = []

    def add_monitors(self):
        """Добавить все мониторы"""
        self.monitors = [
            ShalomSiteMonitor(),
            AfishaMonitor(),
            MosbiletMonitor(),
            TelegramChannelMonitor(),
            VKGroupMonitor()
        ]
        logger.info(f"✓ Добавлено мониторов: {len(self.monitors)}")

    async def start_all(self):
        """Запустить все мониторы"""
        logger.info("🚀 Запуск всех мониторов...")

        for monitor in self.monitors:
            task = asyncio.create_task(monitor.run())
            self.tasks.append(task)

        logger.info(f"✓ Запущено задач мониторинга: {len(self.tasks)}")

    async def stop_all(self):
        """Остановить все мониторы"""
        logger.info("⏹ Остановка всех мониторов...")

        for task in self.tasks:
            task.cancel()

        # Ожидание завершения всех задач
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("✓ Все мониторы остановлены")
