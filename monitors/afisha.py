"""
Монитор Afisha.ru
Отслеживает страницу спектакля "Жирная Люба" и расписание театра
"""

from monitors.base_monitor import BaseMonitor
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from config.settings import settings
import logging
import re
import json

logger = logging.getLogger(__name__)


class AfishaMonitor(BaseMonitor):
    """Монитор Afisha.ru"""

    def __init__(self):
        super().__init__(source_name='afisha')
        self.performance_url = settings.AFISHA_PERFORMANCE_URL
        self.known_events = set()

    async def check_source(self) -> List[Dict[str, Any]]:
        """Проверка страницы спектакля на Afisha"""
        response = await self.make_request(self.performance_url)

        if not response:
            return []

        try:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')

            events = self._parse_schedule(soup)

            # Дополнительно пытаемся найти JSON данные в странице
            json_events = self._extract_json_data(html)
            events.extend(json_events)

            return events

        except Exception as e:
            logger.error(f"✗ {self.source_name}: ошибка парсинга: {e}")
            return []

    def _parse_schedule(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Парсинг блока расписания

        Args:
            soup: BeautifulSoup объект страницы

        Returns:
            Список событий с билетами
        """
        events = []

        # Afisha.ru обычно использует специальные блоки для расписания
        schedule_blocks = soup.find_all(['div', 'article', 'li'],
                                       class_=re.compile(r'event|schedule|session|show-time', re.I))

        # Также ищем кнопки "Билеты"
        ticket_buttons = soup.find_all(['a', 'button'],
                                      text=re.compile(r'билеты|купить|tickets', re.I))

        # Объединяем оба подхода
        potential_blocks = list(schedule_blocks) + [btn.find_parent() for btn in ticket_buttons]

        logger.debug(f"{self.source_name}: найдено блоков расписания: {len(potential_blocks)}")

        for block in potential_blocks:
            if not block:
                continue

            block_text = block.get_text()

            # Ищем ссылку на билеты
            ticket_link = None
            for link in block.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text().strip().lower()

                # Проверяем, это ссылка на билеты
                if 'билет' in link_text or 'ticket' in link_text or 'купить' in link_text:
                    ticket_link = href
                    break

                # Или ссылка ведет на билетную систему
                if any(domain in href for domain in ['afisha.ru/order', 'timepad.ru', 'kassir.ru']):
                    ticket_link = href
                    break

            if not ticket_link:
                continue

            # Делаем ссылку абсолютной
            if ticket_link.startswith('/'):
                ticket_link = 'https://www.afisha.ru' + ticket_link
            elif not ticket_link.startswith('http'):
                ticket_link = 'https://www.afisha.ru/' + ticket_link

            # Проверяем новизну
            if ticket_link in self.known_events:
                continue

            # Извлекаем дату и время
            event_date = self._extract_date(block_text)
            venue = self._extract_venue(block_text)

            event = {
                'source': self.source_name,
                'url': ticket_link,
                'event_date': event_date,
                'venue': venue,
                'raw_text': block_text[:200]
            }

            events.append(event)
            self.known_events.add(ticket_link)

            logger.info(f"✓ {self.source_name}: новое событие - {venue}, {event_date}")

        return events

    def _extract_json_data(self, html: str) -> List[Dict[str, Any]]:
        """
        Попытка извлечь структурированные данные из JSON в HTML

        Args:
            html: HTML код страницы

        Returns:
            Список событий
        """
        events = []

        # Afisha часто встраивает JSON-LD для SEO
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)

                # Проверяем, это Event schema
                if isinstance(data, dict) and data.get('@type') == 'Event':
                    # Извлекаем информацию о билетах
                    offers = data.get('offers', {})
                    if isinstance(offers, dict):
                        url = offers.get('url')
                        availability = offers.get('availability', '')

                        # Проверяем доступность
                        if url and 'InStock' in availability:
                            if url not in self.known_events:
                                event = {
                                    'source': self.source_name,
                                    'url': url,
                                    'event_date': data.get('startDate'),
                                    'venue': data.get('location', {}).get('name', 'Неизвестно'),
                                    'raw_text': 'Extracted from JSON-LD'
                                }
                                events.append(event)
                                self.known_events.add(url)
                                logger.info(f"✓ {self.source_name}: событие из JSON-LD")

            except json.JSONDecodeError:
                continue

        return events

    def _extract_date(self, text: str) -> Optional[str]:
        """Извлечь дату из текста"""
        patterns = [
            r'(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)[а-я]*\s*,?\s*(\d{1,2}:\d{2})?',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
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
            'Шалом',
            'Большая сцена',
            'Малая сцена',
            'Новая сцена'
        ]

        text_lower = text.lower()
        for venue in venues:
            if venue.lower() in text_lower:
                return venue

        return "Театр Шалом"
