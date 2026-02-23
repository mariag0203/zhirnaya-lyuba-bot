"""
Монитор Мосбилет (bilet.mos.ru)
Отслеживает события театра "Шалом" на портале bilet.mos.ru
"""

from monitors.base_monitor import BaseMonitor
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from config.settings import settings
import logging
import re
import json

logger = logging.getLogger(__name__)


class MosbiletMonitor(BaseMonitor):
    """Монитор Мосбилет"""

    def __init__(self):
        super().__init__(source_name='mosbilet')
        self.base_url = settings.MOSBILET_BASE_URL
        self.known_events = set()

        # Известные ID событий (можно добавлять вручную в конфиг)
        self.event_ids = []  # Например: ['381336257']

    async def check_source(self) -> List[Dict[str, Any]]:
        """Проверка событий на Мосбилет"""
        events = []

        # Стратегия 1: Проверка известных ID событий
        for event_id in self.event_ids:
            event_url = f"{self.base_url}/event/{event_id}/"
            event_data = await self._check_event_page(event_url, event_id)
            if event_data:
                events.append(event_data)

        # Стратегия 2: Поиск по организатору
        search_events = await self._search_by_organizer()
        events.extend(search_events)

        return events

    async def _check_event_page(self, url: str, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Проверить страницу конкретного события

        Args:
            url: URL страницы события
            event_id: ID события

        Returns:
            Данные события или None
        """
        response = await self.make_request(url)

        if not response:
            return None

        try:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')

            # Проверяем название события
            title = soup.find(['h1', 'h2'], class_=re.compile(r'title|name|event', re.I))
            if not title:
                title = soup.find('h1')

            if not title:
                return None

            title_text = title.get_text().strip()

            # Проверяем, это "Жирная Люба"
            if not any(keyword.lower() in title_text.lower()
                      for keyword in settings.KEYWORDS_REQUIRED):
                return None

            # Ищем кнопку покупки
            buy_button = soup.find(['a', 'button'],
                                  text=re.compile(r'купить|билеты|заказать', re.I))

            if not buy_button:
                # Альтернативный поиск по классам
                buy_button = soup.find(['a', 'button'],
                                      class_=re.compile(r'buy|ticket|order|purchase', re.I))

            # Проверяем статус доступности
            availability_text = soup.get_text()

            # Признаки того, что билеты НЕ доступны
            unavailable_markers = [
                'нет билетов',
                'sold out',
                'распродано',
                'продажа завершена',
                'мероприятие состоялось'
            ]

            is_unavailable = any(marker in availability_text.lower()
                                for marker in unavailable_markers)

            # Если билеты недоступны и нет кнопки покупки - пропускаем
            if is_unavailable and not buy_button:
                return None

            # Если есть кнопка покупки или билеты доступны
            if buy_button or not is_unavailable:
                # Проверяем новизну
                if url in self.known_events:
                    return None

                # Извлекаем дату и площадку
                event_date = self._extract_date(availability_text)
                venue = self._extract_venue(availability_text)

                self.known_events.add(url)

                logger.info(f"✓ {self.source_name}: новое событие #{event_id}")

                return {
                    'source': self.source_name,
                    'url': url,
                    'event_date': event_date,
                    'venue': venue,
                    'raw_text': title_text
                }

        except Exception as e:
            logger.error(f"✗ {self.source_name}: ошибка парсинга события {event_id}: {e}")

        return None

    async def _search_by_organizer(self) -> List[Dict[str, Any]]:
        """
        Поиск событий театра "Шалом" через поиск или список организатора

        Returns:
            Список найденных событий
        """
        events = []

        # Пробуем разные варианты поиска
        search_queries = [
            'Жирная Люба',
            'Шалом театр',
            'Московский еврейский театр'
        ]

        for query in search_queries:
            search_url = f"{self.base_url}/search/?q={query.replace(' ', '+')}"

            response = await self.make_request(search_url)

            if not response:
                continue

            try:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')

                # Ищем карточки событий в результатах поиска
                event_cards = soup.find_all(['div', 'article', 'li'],
                                           class_=re.compile(r'event|card|item|result', re.I))

                for card in event_cards:
                    card_text = card.get_text()

                    # Проверяем упоминание "Жирная Люба"
                    if not any(keyword.lower() in card_text.lower()
                              for keyword in settings.KEYWORDS_REQUIRED):
                        continue

                    # Ищем ссылку на событие
                    link = card.find('a', href=re.compile(r'/event/\d+'))

                    if not link:
                        continue

                    event_url = link['href']
                    if not event_url.startswith('http'):
                        event_url = self.base_url + event_url

                    # Извлекаем ID события из URL
                    event_id_match = re.search(r'/event/(\d+)', event_url)
                    if event_id_match:
                        event_id = event_id_match.group(1)

                        # Добавляем в список известных ID для будущих проверок
                        if event_id not in self.event_ids:
                            self.event_ids.append(event_id)
                            logger.info(f"✓ Обнаружен новый ID события: {event_id}")

                    # Проверяем эту страницу события
                    event_data = await self._check_event_page(event_url, event_id)
                    if event_data:
                        events.append(event_data)

            except Exception as e:
                logger.error(f"✗ {self.source_name}: ошибка поиска по '{query}': {e}")

        return events

    def _extract_date(self, text: str) -> Optional[str]:
        """Извлечь дату из текста"""
        patterns = [
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})?',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(0)

        return None

    def _extract_venue(self, text: str) -> str:
        """Извлечь площадку из текста"""
        venues = [
            'Новослободская',
            'Варшавка',
            'Большая сцена',
            'Малая сцена',
            'Новая сцена',
            'Шалом'
        ]

        text_lower = text.lower()
        for venue in venues:
            if venue.lower() in text_lower:
                return venue

        return "Театр Шалом"
