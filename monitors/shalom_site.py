"""
Монитор официального сайта театра "Шалом"
Отслеживает афишу на shalom-theatre.ru и shalom-theatre.ru/#b37860
"""

from monitors.base_monitor import BaseMonitor
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.settings import settings
import logging
import re

logger = logging.getLogger(__name__)


class ShalomSiteMonitor(BaseMonitor):
    """Монитор сайта театра Шалом"""

    def __init__(self):
        super().__init__(source_name='shalom_site')
        self.main_url = settings.SHALOM_SITE_URL
        self.afisha_url = settings.SHALOM_AFISHA_URL
        self.known_events = set()  # Хранение известных событий (URL)

    async def check_source(self) -> List[Dict[str, Any]]:
        """Проверка афиши на сайте театра"""
        events = []

        # Проверяем основную страницу
        main_events = await self._check_page(self.main_url)
        events.extend(main_events)

        # Проверяем страницу афиши с якорем
        afisha_events = await self._check_page(self.afisha_url)
        events.extend(afisha_events)

        return events

    async def _check_page(self, url: str) -> List[Dict[str, Any]]:
        """
        Проверить конкретную страницу

        Args:
            url: URL страницы для проверки

        Returns:
            Список найденных событий
        """
        response = await self.make_request(url)

        if not response:
            return []

        try:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')

            events = self._parse_afisha(soup, url)
            return events

        except Exception as e:
            logger.error(f"✗ {self.source_name}: ошибка парсинга {url}: {e}")
            return []

    def _parse_afisha(self, soup: BeautifulSoup, page_url: str) -> List[Dict[str, Any]]:
        """
        Парсинг блока афиши

        Args:
            soup: BeautifulSoup объект страницы
            page_url: URL страницы (для логирования)

        Returns:
            Список событий с билетами
        """
        events = []

        # Ищем все блоки событий
        # Структура может быть разной, поэтому используем несколько селекторов
        event_blocks = soup.find_all(['div', 'article', 'section'],
                                     class_=re.compile(r'event|afisha|performance|show', re.I))

        if not event_blocks:
            # Альтернативный поиск - все блоки с ссылками "Купить"
            event_blocks = soup.find_all(text=re.compile(r'купить билет|регистрация|билеты', re.I))
            event_blocks = [block.find_parent() for block in event_blocks if block.find_parent()]

        logger.debug(f"{self.source_name}: найдено потенциальных блоков: {len(event_blocks)}")

        for block in event_blocks:
            # Проверяем, есть ли упоминание "Жирная Люба"
            block_text = block.get_text()

            if not any(keyword.lower() in block_text.lower()
                      for keyword in settings.KEYWORDS_REQUIRED):
                continue

            # Ищем ссылку на покупку билетов
            buy_link = None
            for link in block.find_all('a', href=True):
                link_text = link.get_text().strip().lower()
                if any(word in link_text for word in ['купить', 'билет', 'регистрация']):
                    buy_link = link['href']
                    break

            if not buy_link:
                continue

            # Делаем ссылку абсолютной
            if buy_link.startswith('/'):
                buy_link = self.main_url.rstrip('/') + buy_link
            elif not buy_link.startswith('http'):
                buy_link = self.main_url.rstrip('/') + '/' + buy_link

            # Проверяем, не видели ли мы это событие раньше
            if buy_link in self.known_events:
                continue

            # Пытаемся извлечь дату и площадку
            event_date = self._extract_date(block_text)
            venue = self._extract_venue(block_text)

            event = {
                'source': self.source_name,
                'url': buy_link,
                'event_date': event_date,
                'venue': venue,
                'raw_text': block_text[:200]  # Первые 200 символов для отладки
            }

            events.append(event)
            self.known_events.add(buy_link)

            logger.info(f"✓ {self.source_name}: новое событие - {venue}, {event_date}")

        return events

    def _extract_date(self, text: str) -> Optional[str]:
        """
        Извлечь дату из текста

        Args:
            text: Текст блока события

        Returns:
            Дата в виде строки или None
        """
        # Паттерны для поиска даты
        patterns = [
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(0)

        return None

    def _extract_venue(self, text: str) -> str:
        """
        Извлечь площадку из текста

        Args:
            text: Текст блока события

        Returns:
            Название площадки или "Неизвестная площадка"
        """
        venues = [
            'Новослободская',
            'Варшавка',
            'Большая сцена',
            'Малая сцена',
            'Новая сцена'
        ]

        text_lower = text.lower()
        for venue in venues:
            if venue.lower() in text_lower:
                return venue

        return "Неизвестная площадка"
