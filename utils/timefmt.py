"""
Московское время для сообщений и логов.
В базе время хранится в UTC (naive datetime), показывается — по Москве.
В Москве нет перехода на летнее время, поэтому достаточно фиксированного UTC+3.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

MSK = timezone(timedelta(hours=3), 'MSK')
WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']


def now_msk() -> datetime:
    return datetime.now(MSK)


def utc_naive_to_msk(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(MSK)


def fmt_msk(dt: Optional[datetime], with_date: bool = True) -> str:
    """UTC naive datetime из БД -> 'дд.мм чч:мм' по Москве."""
    m = utc_naive_to_msk(dt)
    if m is None:
        return '—'
    return m.strftime('%d.%m %H:%M' if with_date else '%H:%M')


def fmt_show(start: datetime) -> str:
    """Время показа (уже московское, naive) -> '13.10 (вт), 19:00'."""
    return f"{start.strftime('%d.%m')} ({WEEKDAYS[start.weekday()]}), {start.strftime('%H:%M')}"


def parse_site_dt(s: str) -> Optional[datetime]:
    """'2026-10-13 19:00:00' или '2026-10-13T19:00:00' -> naive datetime (время Москвы, как на сайте)."""
    if not s:
        return None
    s = s.strip().replace('T', ' ')[:19]
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s[:len(f) + 2], f)
        except ValueError:
            continue
    return None
