"""
Модуль планировщика задач мониторинга.

Использует APScheduler для организации периодического запуска
мониторов с поддержкой динамического изменения интервалов
(нормальный режим / усиленный при обнаружении билетов).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """Обёртка над APScheduler для управления задачами мониторинга."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def add_monitor(self, monitor_id: str, func: object, interval_seconds: int) -> None:
        """
        Добавляет задачу мониторинга в планировщик.

        Args:
            monitor_id: Уникальный идентификатор задачи.
            func: Асинхронная функция проверки.
            interval_seconds: Интервал запуска в секундах.
        """
        self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=monitor_id,
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info("Задача '%s' добавлена (каждые %ds)", monitor_id, interval_seconds)

    def update_interval(self, monitor_id: str, interval_seconds: int) -> None:
        """Изменяет интервал существующей задачи."""
        job = self._scheduler.get_job(monitor_id)
        if job:
            job.reschedule(trigger=IntervalTrigger(seconds=interval_seconds))
            logger.info("Интервал задачи '%s' изменён на %ds", monitor_id, interval_seconds)

    def start(self) -> None:
        """Запускает планировщик."""
        self._scheduler.start()
        logger.info("Планировщик запущен")

    def shutdown(self) -> None:
        """Останавливает планировщик."""
        self._scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")
