"""
Базовый класс для всех мониторов
Определяет общую логику работы, переключение режимов, обработку ошибок
"""

import asyncio
import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from database.models import MonitoringState, TicketEvent
from database.db import async_session_maker
from config.settings import settings
import logging
import random

logger = logging.getLogger(__name__)


class BaseMonitor(ABC):
    """
    Абстрактный базовый класс для мониторов

    Наследники должны реализовать:
    - check_source(): основная логика проверки источника
    - parse_response(): парсинг ответа от источника
    """

    def __init__(self, source_name: str, bot=None):
        """
        Args:
            source_name: Имя источника (shalom_site, afisha, mosbilet, etc.)
            bot: Объект aiogram Bot для отправки уведомлений
        """
        self.source_name = source_name
        self.bot = bot
        self.mode = 'normal'  # normal или enhanced
        self.enhanced_until: Optional[datetime] = None
        self.error_count = 0
        self.max_errors = 5
        self.current_proxy_index = 0

    async def initialize(self):
        """Инициализация монитора - создание записи в БД"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(MonitoringState).where(MonitoringState.source == self.source_name)
            )
            state = result.scalar_one_or_none()

            if not state:
                state = MonitoringState(
                    source=self.source_name,
                    last_check=datetime.utcnow(),
                    mode='normal'
                )
                session.add(state)
                await session.commit()
                logger.info(f"✓ Монитор {self.source_name} инициализирован")

    def get_interval(self) -> int:
        """Получить текущий интервал проверки в секундах"""
        return max(settings.MIN_INTERVAL, settings.BASE_INTERVAL)

    async def switch_to_enhanced_mode(self, duration: int = None):
        """Усиленный режим отключён: интервал не бывает меньше MIN_INTERVAL."""
        return

    async def check_mode(self):
        """Проверить, не истек ли усиленный режим"""
        if self.mode == 'enhanced' and self.enhanced_until:
            if datetime.utcnow() > self.enhanced_until:
                await self.switch_to_normal_mode()

    async def switch_to_normal_mode(self):
        """Переключить в обычный режим мониторинга"""
        self.mode = 'normal'
        self.enhanced_until = None

        async with async_session_maker() as session:
            await session.execute(
                update(MonitoringState)
                .where(MonitoringState.source == self.source_name)
                .values(mode='normal')
            )
            await session.commit()

        logger.info(f"🟢 {self.source_name}: возврат в обычный режим")

    def get_proxy(self) -> Optional[str]:
        """
        Получить следующий прокси из пула (ротация)

        Returns:
            URL прокси или None
        """
        return None  # прокси не используются

    async def make_request(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Выполнить HTTP запрос с обработкой ошибок и прокси

        Args:
            url: URL для запроса
            method: HTTP метод
            headers: Заголовки запроса
            **kwargs: Дополнительные параметры для aiohttp

        Returns:
            HTML-текст страницы или None при ошибке
        """
        proxy = self.get_proxy()

        default_headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
            ),
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        if headers:
            default_headers.update(headers)

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=default_headers,
                    proxy=proxy,
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    self.error_count = 0  # Сброс счетчика ошибок при успехе
                    # Читаем текст ВНУТРИ контекста, пока соединение открыто
                    return await response.text()

        except asyncio.TimeoutError:
            self.error_count += 1
            logger.warning(f"⏱ {self.source_name}: timeout для {url}")
            return None

        except aiohttp.ClientError as e:
            self.error_count += 1
            logger.warning(f"⚠️ {self.source_name}: ошибка запроса {url}: {e}")
            return None

        except Exception as e:
            self.error_count += 1
            logger.error(f"✗ {self.source_name}: неожиданная ошибка {url}: {e}")
            return None

    async def update_state(self, success: bool = True, error_text: str = None):
        """
        Обновить состояние монитора в БД

        Args:
            success: Успешна ли была проверка
            error_text: Текст ошибки (если есть)
        """
        async with async_session_maker() as session:
            values = {
                'last_check': datetime.utcnow(),
                'error_count': self.error_count
            }

            if success:
                values['last_success'] = datetime.utcnow()
                values['last_error'] = None
            elif error_text:
                values['last_error'] = error_text

            await session.execute(
                update(MonitoringState)
                .where(MonitoringState.source == self.source_name)
                .values(**values)
            )
            await session.commit()

    async def _send_notifications(self, events: List[Dict[str, Any]]):
        """
        Отправить уведомления пользователям о найденных событиях

        Args:
            events: Список новых событий из check_source()
        """
        if not self.bot:
            logger.debug(f"{self.source_name}: bot не установлен, уведомления пропущены")
            return

        from bot.notifications import notify_seats_available
        for event in events:
            try:
                await notify_seats_available(self.bot, event)
            except Exception as e:
                logger.error(f"✗ {self.source_name}: ошибка отправки уведомления: {e}")

    @abstractmethod
    async def check_source(self) -> List[Dict[str, Any]]:
        """
        Основной метод проверки источника
        Должен быть реализован в наследниках

        Returns:
            Список найденных событий (билетов)
        """
        pass

    async def run(self):
        """
        Основной цикл мониторинга
        Вызывает check_source() с заданным интервалом
        """
        await self.initialize()

        logger.info(f"🚀 Запуск монитора: {self.source_name}")

        consecutive_failures = 0
        alerted = False

        while True:
            try:
                events = await self.check_source()

                if events:
                    logger.info(f"🎫 {self.source_name}: найдено событий: {len(events)}")
                    await self._send_notifications(events)

                await self.update_state(success=True)

                if alerted:
                    await self._alert_admin(f"✅ {self.source_name}: проверки снова проходят успешно")
                consecutive_failures, alerted = 0, False

                interval = self.get_interval()
                await asyncio.sleep(interval + random.uniform(0, 5))

            except asyncio.CancelledError:
                raise
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"✗ {self.source_name}: ошибка проверки ({consecutive_failures} подряд): {e}")
                try:
                    await self.update_state(success=False, error_text=str(e))
                except Exception:
                    pass

                if consecutive_failures >= 5 and not alerted:
                    await self._alert_admin(
                        f"⚠️ {self.source_name}: {consecutive_failures} неудачных проверок подряд.\n"
                        f"Последняя ошибка: {e}"
                    )
                    alerted = True

                # При ошибках ждём дольше обычного: от интервала до 15 минут
                backoff = min(900, self.get_interval() * (2 ** min(consecutive_failures - 1, 4)))
                await asyncio.sleep(backoff)

    async def _alert_admin(self, text: str):
        if not self.bot or not settings.ADMIN_CHAT_ID:
            return
        try:
            await self.bot.send_message(settings.ADMIN_CHAT_ID, text, parse_mode=None)
        except Exception as e:
            logger.error(f"✗ не удалось отправить сообщение администратору: {e}")
