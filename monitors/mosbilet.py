"""
Монитор Мосбилета (bilet.mos.ru) для одного спектакля.

Источники (те же, что использует сама страница https://bilet.mos.ru/event/<ID>/):
  1. /api/newsfeed/v4/frontend/json/ru/afisha/<ID>
       карточка события: ebs_id и agent_uid в билетной системе, общий флаг
       «есть места», дата открытия продаж
  2. /api/newsfeed/v4/frontend/json/ru/afisha/<ID>/occurrences
       ВСЕ показы с датой и временем, в том числе распроданные. По этому списку бот
       узнаёт о новых показах (26.09 внеплановый показ на 27.09 появился именно здесь).
  3. https://tickets-external.mos.ru/api/widget/v2/event/<ebs_id>/performances
       расписание из билетной системы: по каждому показу, на который ЕСТЬ места,
       число свободных мест и минимальная цена в рублях. Распроданные показы сюда
       не попадают, поэтому их нет — значит 0 мест.

Три GET-запроса за цикл, цикл раз в BASE_INTERVAL секунд (не чаще раза в минуту).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from config.settings import settings
from database.db import async_session_maker
from database.models import Show
from monitors.base_monitor import BaseMonitor, RequestError
from utils.timefmt import now_msk, parse_site_dt, fmt_show

logger = logging.getLogger(__name__)

NEWSFEED = '/api/newsfeed/v4/frontend/json/ru/afisha'
PERF_DAYS_PER_PAGE = 10


class ParseError(Exception):
    """Ответ пришёл, но в нём не то, что мы ожидаем (похоже, сайт поменялся)."""


@dataclass
class SeatInfo:
    performance_id: Optional[int]
    free_seats: int
    min_price: Optional[int]


class MosbiletMonitor(BaseMonitor):
    def __init__(self, bot=None):
        super().__init__(source_name='mosbilet', bot=bot)
        self.event_id = settings.MOSBILET_EVENT_ID
        self.base_url = settings.MOSBILET_BASE_URL
        self.tickets_url = settings.TICKETS_BASE_URL
        self.empty_alerted = False
        self.opening_date: Optional[datetime] = None
        self.event_title: str = 'Жирная Люба'

    # ---------- получение данных ----------

    async def fetch_event(self) -> Dict[str, Any]:
        data = await self.get_json(f"{self.base_url}{NEWSFEED}/{self.event_id}")
        if not isinstance(data, dict) or data.get('id') != self.event_id:
            raise ParseError('карточка события: нет поля id или id другой')
        if not data.get('ebs_id') or not data.get('ebs_agent_uid'):
            raise ParseError('карточка события: нет ebs_id / ebs_agent_uid')
        return data

    async def fetch_occurrences(self) -> List[datetime]:
        data = await self.get_json(
            f"{self.base_url}{NEWSFEED}/{self.event_id}/occurrences",
            params={'per-page': 50},
        )
        items = data.get('items') if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ParseError('список показов: нет поля items')
        result = []
        for it in items:
            dt = parse_site_dt(it.get('date_from', '')) if isinstance(it, dict) else None
            if dt is None:
                raise ParseError(f'список показов: не разобрать дату в {str(it)[:100]}')
            result.append(dt)
        return result

    async def fetch_seats(self, ebs_id: int, agent_uid: str) -> Dict[datetime, SeatInfo]:
        """Места по показам. Распроданных показов в ответе нет."""
        seats: Dict[datetime, SeatInfo] = {}
        date_from = now_msk().date()
        for _ in range(5):  # страницы по PERF_DAYS_PER_PAGE дней с показами
            data = await self.get_json(
                f"{self.tickets_url}/api/widget/v2/event/{ebs_id}/performances",
                params={
                    'date_from': date_from.isoformat(),
                    'date_to': '',
                    'performances_limit_by_days': PERF_DAYS_PER_PAGE,
                    'agent_id': agent_uid,
                },
            )
            if not isinstance(data, list):
                raise ParseError('билетная система: ожидался список дней')
            for day in data:
                for p in (day or {}).get('performances') or []:
                    dt = parse_site_dt(p.get('start_datetime', ''))
                    free = p.get('free_seats_count')
                    if dt is None or not isinstance(free, int):
                        raise ParseError(f'билетная система: неожиданный показ {str(p)[:120]}')
                    price = p.get('min_performance_price')
                    seats[dt] = SeatInfo(
                        performance_id=p.get('id'),
                        free_seats=max(0, free),
                        min_price=int(price) if isinstance(price, (int, float)) else None,
                    )
            if len(data) < PERF_DAYS_PER_PAGE:
                break
            last = parse_site_dt(data[-1].get('date', '') + ' 00:00')
            if not last:
                break
            date_from = (last + timedelta(days=1)).date()
        return seats

    # ---------- одна проверка ----------

    async def check(self) -> None:
        try:
            event = await self.fetch_event()
            occurrences = await self.fetch_occurrences()
        except ParseError as e:
            await self._register_empty(f"ответ сайта не разобран: {e}")
            raise

        self.event_title = event.get('title') or self.event_title
        self.opening_date = parse_site_dt(event.get('ebs_opening_date') or '')
        flag = event.get('ebs_has_available_seats')

        try:
            seats = await self.fetch_seats(int(event['ebs_id']), str(event['ebs_agent_uid']))
            self.health.seats_source_ok = True
        except (RequestError, ParseError) as e:
            # Без билетной системы новые показы всё равно видны; места — нет.
            logger.warning(f"{self.source_name}: места по показам не получены: {e}")
            self.health.seats_source_ok = False
            self.health.last_error = f"места по показам не получены: {e}"
            seats = None

        now = now_msk().replace(tzinfo=None)
        shows = {dt for dt in occurrences if dt > now}
        if seats:
            shows |= {dt for dt in seats if dt > now}

        if not any(dt > now for dt in occurrences):
            # Даже если билетная система что-то вернула: пустой список показов
            # на странице события — признак, что разбор сломался
            await self._register_empty('в расписании на странице спектакля не найдено ни одного будущего показа')
        else:
            await self._register_found()

        await self.sync_shows(sorted(shows), seats)

        total = sum(s.free_seats for s in (seats or {}).values())
        self.health.shows_found = len(shows)
        self.health.free_seats_total = total
        summary = ', '.join(
            f"{d:%d.%m %H:%M}={seats[d].free_seats if seats and d in seats else (0 if seats is not None else '?')}"
            for d in sorted(shows)
        ) or 'нет'
        logger.info(f"{self.source_name}: показов {len(shows)}, места: {summary}; флаг афиши: {flag}")
        if seats is not None and bool(flag) != (total > 0):
            logger.info(f"{self.source_name}: флаг афиши ({flag}) расходится с билетной системой ({total} мест)")

    async def _register_empty(self, reason: str):
        h = self.health
        h.consecutive_empty += 1
        if h.consecutive_empty >= settings.PARSE_ALERT_AFTER and not self.empty_alerted:
            self.empty_alerted = True
            await self.alert_admin(
                f"⚠️ Мосбилет: {h.consecutive_empty} проверок подряд — {reason}.\n"
                "Скорее всего, сайт поменял вёрстку или API, и бот сейчас ничего не видит. "
                "Если показы спектакля просто закончились, это тоже объяснение.\n"
                f"{settings.event_url}"
            )

    async def _register_found(self):
        if self.empty_alerted:
            await self.alert_admin("✅ Мосбилет: показы снова находятся, разбор работает")
        self.empty_alerted = False
        self.health.consecutive_empty = 0

    # ---------- сравнение с базой и уведомления ----------

    async def sync_shows(self, shows: List[datetime], seats: Optional[Dict[datetime, SeatInfo]]):
        from bot.notifications import notify_new_show, notify_seats

        utcnow = datetime.utcnow()
        cooldown = timedelta(minutes=settings.NOTIFY_COOLDOWN_MIN)
        to_notify_new: List[Show] = []
        to_notify_seats: List[Show] = []

        async with async_session_maker() as session:
            res = await session.execute(select(Show).where(Show.event_id == self.event_id))
            rows = {r.starts_at: r for r in res.scalars().all()}
            first_run = not rows

            for dt in shows:
                info = seats.get(dt) if seats is not None else None
                row = rows.get(dt)
                if row is None:
                    row = Show(event_id=self.event_id, starts_at=dt, free_seats=0,
                               first_seen_at=utcnow, last_seen_at=utcnow, is_listed=True)
                    session.add(row)
                    rows[dt] = row
                    logger.info(f"{self.source_name}: новый показ {dt:%d.%m.%Y %H:%M}")
                    if not first_run:
                        to_notify_new.append(row)
                elif not row.is_listed:
                    row.is_listed = True
                    logger.info(f"{self.source_name}: показ {dt:%d.%m.%Y %H:%M} снова в расписании")

                row.last_seen_at = utcnow
                if seats is None:
                    continue  # мест не знаем — состояние не трогаем

                prev = row.free_seats or 0
                now_free = info.free_seats if info else 0
                if info:
                    row.performance_id = info.performance_id or row.performance_id
                    row.min_price = info.min_price
                if now_free != prev:
                    row.free_seats = now_free
                    row.seats_changed_at = utcnow
                    logger.info(f"{self.source_name}: {dt:%d.%m %H:%M} мест {prev} -> {now_free}")

                if prev == 0 and now_free > 0 and row not in to_notify_new:
                    recent = row.last_seats_notified_at and utcnow - row.last_seats_notified_at < cooldown
                    if recent:
                        logger.info(f"{self.source_name}: {dt:%d.%m %H:%M} — места снова есть, "
                                    f"но уведомление было меньше {settings.NOTIFY_COOLDOWN_MIN} мин назад")
                    else:
                        to_notify_seats.append(row)

            listed = set(shows)
            for dt, row in rows.items():
                if row.is_listed and dt not in listed:
                    row.is_listed = False
                    logger.info(f"{self.source_name}: показ {dt:%d.%m.%Y %H:%M} пропал из расписания "
                                f"(прошёл или снят)")

            for row in to_notify_new + to_notify_seats:
                if (row.free_seats or 0) > 0:
                    row.last_seats_notified_at = utcnow
            await session.commit()

        if first_run and shows:
            await self.alert_admin(
                "Начинаю следить за показами «" + self.event_title + "»:\n" +
                '\n'.join(f"• {fmt_show(dt)} — мест: "
                          f"{rows[dt].free_seats if seats is not None else '?'}" for dt in shows)
            )

        for row in to_notify_new:
            self.health.day_notifications += 1
            await notify_new_show(self.bot, row, self.opening_date, settings.event_url,
                                  seats_known=seats is not None)
        for row in to_notify_seats:
            self.health.day_notifications += 1
            await notify_seats(self.bot, row, settings.event_url)
