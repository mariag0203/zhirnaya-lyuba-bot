"""
Рассылка уведомлений подписчикам
"""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select, update

from config.settings import settings
from database.db import async_session_maker
from database.models import User, NotificationLog, Show
from utils.timefmt import fmt_show, now_msk

logger = logging.getLogger(__name__)


async def broadcast(bot: Optional[Bot], message: str, notification_type: str,
                    show_id: Optional[int] = None) -> int:
    """Отправить сообщение всем подписчикам (и администратору). Возвращает число доставленных."""
    if bot is None:
        logger.info(f"(бот не задан, рассылка пропущена) {message!r}")
        return 0

    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.is_subscribed == True))  # noqa: E712
        chat_ids = [u.chat_id for u in res.scalars().all()]
    if settings.ADMIN_CHAT_ID and settings.ADMIN_CHAT_ID not in chat_ids:
        chat_ids.append(settings.ADMIN_CHAT_ID)

    ok, failed, blocked = 0, [], []
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=None,
                                   disable_web_page_preview=True)
            ok += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — больше ему не пишем
            blocked.append(chat_id)
        except Exception as e:
            failed.append(chat_id)
            logger.error(f"✗ Ошибка отправки {chat_id}: {e}")

    async with async_session_maker() as session:
        if blocked:
            await session.execute(update(User).where(User.chat_id.in_(blocked)).values(is_subscribed=False))
            logger.info(f"Бота заблокировали, отписаны: {blocked}")
        session.add(NotificationLog(
            event_id=show_id,
            notification_type=notification_type,
            message=message,
            recipients_count=ok,
            sent_at=datetime.utcnow(),
            success=not failed,
            error_text=f"Failed for: {failed}" if failed else None,
        ))
        await session.commit()

    logger.info(f"📨 Рассылка ({notification_type}): {ok}/{len(chat_ids)} доставлено")
    return ok


def _seats_line(show: Show) -> str:
    n = show.free_seats or 0
    line = f"{n} {plural(n, 'место', 'места', 'мест')}"
    if show.min_price:
        line += f", от {show.min_price} ₽"
    return line


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


async def notify_new_show(bot: Optional[Bot], show: Show, opening_date: Optional[datetime],
                          url: str, seats_known: bool = True) -> int:
    lines = [
        "🆕 Новый показ «Жирной Любы»",
        f"{fmt_show(show.starts_at)}",
        "",
    ]
    if (show.free_seats or 0) > 0:
        lines.append(f"Сейчас свободно: {_seats_line(show)}")
    elif opening_date and opening_date > now_msk().replace(tzinfo=None):
        lines.append(f"Продажа на Мосбилете откроется {opening_date:%d.%m в %H:%M}")
    elif seats_known:
        lines.append("Свободных мест на Мосбилете сейчас нет")
    lines += ["", f"Выбор мест: {url}", f"(в расписании на странице выберите {show.starts_at:%d.%m})"]
    return await broadcast(bot, "\n".join(lines), 'new_show', show.id)


async def notify_seats(bot: Optional[Bot], show: Show, url: str) -> int:
    text = (
        f"🎫 {fmt_show(show.starts_at)} — появилось {_seats_line(show)}\n"
        f"\n"
        f"Выбор мест: {url}\n"
        f"(в расписании на странице выберите {show.starts_at:%d.%m})"
    )
    return await broadcast(bot, text, 'seats', show.id)
