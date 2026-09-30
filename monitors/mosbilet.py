"""
Монитор Мосбилет (bilet.mos.ru)

Использует тот же публичный JSON-эндпоинт, которым пользуется сам сайт:
  /api/newsfeed/v4/frontend/json/ru/afisha
Один GET за цикл: фильтр по точному названию спектакля находит все
актуальные события (в т.ч. новые ID), а поле ebs_has_available_seats
показывает, есть ли свободные места.

Уведомление отправляется при переходе «мест нет» -> «места есть»
(и при первом обнаружении события, если места уже есть).
Состояние хранится в БД, поэтому перезапуск не вызывает повторных уведомлений.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from config.settings import settings
from database.db import async_session_maker
from database.models import TicketEvent
from monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

API_PATH = '/api/newsfeed/v4/frontend/json/ru/afisha'
FIELDS = 'id,title,date_from,date_to,ebs_has_available_seats,ebs_price_from,ebs_price_to'


class MosbiletMonitor(BaseMonitor):
    """Монитор Мосбилет через JSON API афиши mos.ru"""

    def __init__(self, bot=None):
        super().__init__(source_name='mosbilet', bot=bot)
        self.base_url = settings.MOSBILET_BASE_URL
        self.title = settings.MOSBILET_TITLE
        self.extra_ids = settings.MOSBILET_EVENT_IDS

    def _build_url(self, flt: Dict[str, Any]) -> str:
        from urllib.parse import urlencode
        query = urlencode({
            'fields': FIELDS,
            'filter': json.dumps(flt, ensure_ascii=False),
            'per-page': 50,
        })
        return f"{self.base_url}{API_PATH}?{query}"

    async def fetch_items(self) -> Optional[List[Dict[str, Any]]]:
        """Получить события: по названию + явно заданные ID. None при ошибке."""
        flt: Dict[str, Any] = {'title': self.title}
        text = await self.make_request(
            self._build_url(flt),
            headers={'Accept': 'application/json'},
        )
        if text is None:
            return None
        items = self.parse_items(text)
        if items is None:
            return None

        # Явно заданные ID (на случай, если название на сайте отличается) —
        # отдельным запросом, т.к. фильтр API не поддерживает OR.
        if self.extra_ids:
            text2 = await self.make_request(
                self._build_url({'id': [int(i) for i in self.extra_ids]}),
                headers={'Accept': 'application/json'},
            )
            extra = self.parse_items(text2) if text2 else None
            if extra:
                known = {it['id'] for it in items}
                items.extend(it for it in extra if it['id'] not in known)
        return items

    def parse_items(self, text: str) -> Optional[List[Dict[str, Any]]]:
        try:
            data = json.loads(text)
            items = data.get('items')
            if not isinstance(items, list):
                raise ValueError('нет поля items')
            return [it for it in items if isinstance(it, dict) and 'id' in it]
        except Exception as e:
            logger.error(f"✗ {self.source_name}: не удалось разобрать ответ API: {e}")
            self.error_count += 1
            return None

    @staticmethod
    def _fmt_dates(item: Dict[str, Any]) -> str:
        def d(s):
            try:
                return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
            except Exception:
                return s or '?'
        a, b = item.get('date_from'), item.get('date_to')
        if a and b and a[:10] != b[:10]:
            return f"{d(a)} — {d(b)}"
        return d(a)

    async def check_source(self) -> List[Dict[str, Any]]:
        items = await self.fetch_items()
        if items is None:
            raise RuntimeError('запрос к API Мосбилета не удался')

        new_events: List[Dict[str, Any]] = []
        async with async_session_maker() as session:
            for item in items:
                url = f"{self.base_url}/event/{item['id']}/"
                available = bool(item.get('ebs_has_available_seats'))
                status = 'available' if available else 'sold_out'

                res = await session.execute(
                    select(TicketEvent).where(
                        TicketEvent.source == self.source_name,
                        TicketEvent.url == url,
                    )
                )
                row = res.scalar_one_or_none()
                prev = row.status if row else None

                if row is None:
                    row = TicketEvent(source=self.source_name, url=url,
                                      venue=item.get('title'), status=status)
                    session.add(row)
                    logger.info(f"{self.source_name}: новое событие #{item['id']} ({status})")
                elif prev != status:
                    logger.info(f"{self.source_name}: #{item['id']} {prev} -> {status}")
                    row.status = status

                if available and prev != 'available':
                    price = item.get('ebs_price_from')
                    new_events.append({
                        'source': self.source_name,
                        'url': url,
                        'event_date': self._fmt_dates(item),
                        'venue': 'Театр «Шалом»',
                        'price_from': (price // 100) if isinstance(price, int) else None,
                        'returned': prev == 'sold_out',
                    })
            await session.commit()

        logger.info(
            f"{self.source_name}: проверено событий: {len(items)}, "
            f"с местами: {sum(1 for i in items if i.get('ebs_has_available_seats'))}"
        )
        return new_events
