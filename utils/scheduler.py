"""
Запуск монитора Мосбилета и ежедневного сообщения «я работаю»
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from config.settings import settings
from monitors import MosbiletMonitor
from utils.timefmt import now_msk, fmt_msk

logger = logging.getLogger(__name__)


class MonitorScheduler:
    def __init__(self):
        self.monitor: Optional[MosbiletMonitor] = None
        self.tasks: List[asyncio.Task] = []

    def add_monitors(self, bot=None) -> MosbiletMonitor:
        self.monitor = MosbiletMonitor(bot=bot)
        return self.monitor

    @property
    def monitors(self):
        return [self.monitor] if self.monitor else []

    async def start_all(self):
        self.tasks.append(asyncio.create_task(self.monitor.run()))
        if 0 <= settings.HEARTBEAT_HOUR <= 23:
            self.tasks.append(asyncio.create_task(self.heartbeat()))

    async def stop_all(self):
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("✓ Мониторинг остановлен")

    async def heartbeat(self):
        """Раз в сутки в HEARTBEAT_HOUR по Москве — короткий отчёт администратору."""
        while True:
            now = now_msk()
            nxt = now.replace(hour=settings.HEARTBEAT_HOUR, minute=0, second=0, microsecond=0)
            if nxt <= now:
                nxt += timedelta(days=1)
            await asyncio.sleep((nxt - now).total_seconds())
            try:
                await self.send_heartbeat()
            except Exception as e:
                logger.error(f"✗ ежедневный отчёт не отправлен: {e}")

    def heartbeat_problems(self) -> List[str]:
        """Только устойчивые проблемы. Разовый сбой связи, после которого следующая
        проверка прошла, проблемой не считается."""
        h = self.monitor.health
        problems = []
        if h.consecutive_failures >= 3:
            problems.append(f"проверки не проходят уже {h.consecutive_failures} раз подряд: {h.last_error}")
        if h.consecutive_empty >= settings.PARSE_ALERT_AFTER:
            problems.append(f"{h.consecutive_empty} проверок подряд не находят ни одного показа — "
                            "возможно, сайт поменялся")
        if h.consecutive_seats_failures >= 5:
            problems.append(f"билетная система не отвечает {h.consecutive_seats_failures} проверок подряд — "
                            "места по показам не видны")
        return problems

    def heartbeat_text(self) -> str:
        h = self.monitor.health
        text = (
            f"🟢 Я работаю. За сутки проверок: {h.day_checks}, уведомлений: {h.day_notifications}.\n"
            f"Показов вижу: {h.shows_found}, свободных мест: {h.free_seats_total}. "
            f"Последняя успешная проверка: {fmt_msk(h.last_ok_at)} МСК."
        )
        if h.day_failures or h.day_seats_failures:
            text += (f"\nРазовые сбои связи: {h.day_failures} проверок не прошли целиком, "
                     f"в {h.day_seats_failures} не ответила билетная система. "
                     "Бот повторял проверку, это нормально.")
        problems = self.heartbeat_problems()
        if problems:
            text += "\n⚠️ Сейчас есть проблема: " + "; ".join(problems)
        return text

    async def send_heartbeat(self):
        await self.monitor.alert_admin(self.heartbeat_text())
        h = self.monitor.health
        h.day_checks = h.day_failures = h.day_seats_failures = h.day_notifications = 0
