"""
Базовый цикл монитора: опрос раз в BASE_INTERVAL (не чаще раза в 60 с),
HTTP-запросы напрямую с IP сервера, учёт ошибок и оповещение администратора.
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from sqlalchemy import select, update

from config.settings import settings
from database.db import async_session_maker
from database.models import MonitoringState

logger = logging.getLogger(__name__)

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


class RequestError(Exception):
    pass


@dataclass
class Health:
    """То, что бот реально нашёл на последних проверках. Читается командой /status."""
    started_at: datetime = field(default_factory=datetime.utcnow)
    checks_total: int = 0
    checks_failed: int = 0
    consecutive_failures: int = 0
    consecutive_empty: int = 0          # проверок подряд, где не найдено ни одного показа
    last_check_at: Optional[datetime] = None
    last_ok_at: Optional[datetime] = None
    last_error: Optional[str] = None
    shows_found: int = 0
    free_seats_total: int = 0
    seats_source_ok: Optional[bool] = None   # ответила ли билетная система (места по показам)
    consecutive_seats_failures: int = 0      # проверок подряд без ответа билетной системы
    notes: List[str] = field(default_factory=list)
    # счётчики за сутки для ежедневного «я работаю»
    day_checks: int = 0
    day_failures: int = 0
    day_seats_failures: int = 0
    day_notifications: int = 0


class BaseMonitor(ABC):
    def __init__(self, source_name: str, bot=None):
        self.source_name = source_name
        self.bot = bot
        self.health = Health()

    async def initialize(self):
        async with async_session_maker() as session:
            res = await session.execute(
                select(MonitoringState).where(MonitoringState.source == self.source_name)
            )
            if res.scalar_one_or_none() is None:
                session.add(MonitoringState(source=self.source_name, last_check=datetime.utcnow()))
                await session.commit()

    def get_interval(self) -> int:
        return max(settings.MIN_INTERVAL, settings.BASE_INTERVAL)

    async def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET и разбор JSON. Бросает RequestError с понятным текстом."""
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        raise RequestError(f"HTTP {resp.status} от {url.split('/')[2]}")
                    return await resp.json(content_type=None)
        except asyncio.TimeoutError:
            raise RequestError(f"таймаут {url.split('/')[2]}")
        except aiohttp.ClientError as e:
            raise RequestError(f"{url.split('/')[2]}: {e}")
        except ValueError as e:
            raise RequestError(f"{url.split('/')[2]}: ответ не JSON ({e})")

    async def update_state(self, success: bool, error_text: Optional[str] = None):
        now = datetime.utcnow()
        values: Dict[str, Any] = {'last_check': now, 'error_count': self.health.consecutive_failures}
        if success:
            values['last_success'] = now
            values['last_error'] = None
        elif error_text:
            values['last_error'] = error_text
        async with async_session_maker() as session:
            await session.execute(
                update(MonitoringState)
                .where(MonitoringState.source == self.source_name)
                .values(**values)
            )
            await session.commit()

    @abstractmethod
    async def check(self) -> None:
        """Одна проверка. Бросает исключение при сбое."""

    async def run(self):
        await self.initialize()
        logger.info(f"🚀 Запуск монитора {self.source_name}, интервал {self.get_interval()} с")
        failure_alerted = False

        while True:
            h = self.health
            h.checks_total += 1
            h.day_checks += 1
            h.last_check_at = datetime.utcnow()
            try:
                await self.check()
                h.last_ok_at = h.last_check_at
                h.last_error = None
                if failure_alerted:
                    await self.alert_admin(f"✅ {self.source_name}: проверки снова проходят")
                    failure_alerted = False
                h.consecutive_failures = 0
                await self.update_state(success=True)
                await asyncio.sleep(self.get_interval() + random.uniform(0, 5))

            except asyncio.CancelledError:
                raise
            except Exception as e:
                h.checks_failed += 1
                h.day_failures += 1
                h.consecutive_failures += 1
                h.last_error = str(e)
                logger.error(f"✗ {self.source_name}: ошибка проверки ({h.consecutive_failures} подряд): {e}")
                try:
                    await self.update_state(success=False, error_text=str(e))
                except Exception:
                    pass
                if h.consecutive_failures >= 5 and not failure_alerted:
                    await self.alert_admin(
                        f"⚠️ {self.source_name}: {h.consecutive_failures} неудачных проверок подряд.\n"
                        f"Последняя ошибка: {e}"
                    )
                    failure_alerted = True
                # при ошибках ждём дольше: от интервала до 15 минут
                backoff = min(900, self.get_interval() * (2 ** min(h.consecutive_failures - 1, 4)))
                await asyncio.sleep(backoff)

    async def alert_admin(self, text: str):
        if not self.bot or not settings.ADMIN_CHAT_ID:
            return
        try:
            await self.bot.send_message(settings.ADMIN_CHAT_ID, text, parse_mode=None,
                                        disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"✗ не удалось написать администратору: {e}")
