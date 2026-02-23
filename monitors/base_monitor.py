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

    def __init__(self, source_name: str):
        """
        Args:
            source_name: Имя источника (shalom_site, afisha, mosbilet, etc.)
        """
        self.source_name = source_name
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
        if self.mode == 'enhanced':
            return settings.ENHANCED_INTERVAL
        return settings.BASE_INTERVAL

    async def switch_to_enhanced_mode(self, duration: int = None):
        """
        Переключить в усиленный режим мониторинга

        Args:
            duration: Длительность усиленного режима в секундах
        """
        if duration is None:
            duration = settings.ENHANCED_DURATION

        self.mode = 'enhanced'
        self.enhanced_until = datetime.utcnow() + timedelta(seconds=duration)

        async with async_session_maker() as session:
            await session.execute(
                update(MonitoringState)
                .where(MonitoringState.source == self.source_name)
                .values(mode='enhanced')
            )
            await session.commit()

        logger.info(f"🔥 {self.source_name}: переход в усиленный режим ({duration}с)")

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
        if not settings.PROXY_LIST:
            return None

        proxy = settings.PROXY_LIST[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(settings.PROXY_LIST)
        return proxy

    async def make_request(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Выполнить HTTP запрос с обработкой ошибок и прокси

        Args:
            url: URL для запроса
            method: HTTP метод
            headers: Заголовки запроса
            **kwargs: Дополнительные параметры для aiohttp

        Returns:
            Response объект или None при ошибке
        """
        proxy = self.get_proxy()

        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }

        if headers:
            default_headers.update(headers)

        timeout = aiohttp.ClientTimeout(total=10)

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
                    return response

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

        while True:
            try:
                # Проверка режима (не истек ли enhanced)
                await self.check_mode()

                # Основная проверка
                events = await self.check_source()

                if events:
                    logger.info(f"🎫 {self.source_name}: найдено событий: {len(events)}")

                # Обновление состояния
                await self.update_state(success=True)

                # Небольшая случайная задержка (джиттер)
                interval = self.get_interval()
                jitter = random.uniform(-0.5, 0.5)
                await asyncio.sleep(max(1, interval + jitter))

            except Exception as e:
                logger.error(f"✗ {self.source_name}: критическая ошибка в цикле: {e}")
                await self.update_state(success=False, error_text=str(e))

                # Exponential backoff при ошибках
                backoff = min(60, 5 * (2 ** min(self.error_count, 5)))
                await asyncio.sleep(backoff)
