"""
Команды Telegram-бота
"""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update, func

from config.settings import settings
from database.db import async_session_maker
from database.models import User, Show, MonitoringState
from utils.timefmt import fmt_msk, fmt_show, now_msk
from bot.notifications import plural

logger = logging.getLogger(__name__)
router = Router()

# Монитор, запущенный в main.py; нужен /status, чтобы показать, что бот реально нашёл
MONITOR = {'mosbilet': None}


async def get_or_create_user(message: Message, subscribe: bool = False) -> User:
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.chat_id == message.chat.id))
        user = res.scalar_one_or_none()
        if user is None:
            user = User(chat_id=message.chat.id,
                        username=message.from_user.username if message.from_user else None,
                        first_name=message.from_user.first_name if message.from_user else None,
                        is_subscribed=True)
            session.add(user)
            await session.commit()
            logger.info(f"✓ Новый пользователь: {message.chat.id}")
        elif subscribe and not user.is_subscribed:
            user.is_subscribed = True
            await session.commit()
        return user


@router.message(Command("start"))
async def cmd_start(message: Message):
    await get_or_create_user(message, subscribe=True)
    await message.answer(
        f"Привет! Я слежу за спектаклем «Жирная Люба» театра «Шалом» на Мосбилете "
        f"(проверка раз в {settings.BASE_INTERVAL} с).\n\n"
        "Пишу, когда:\n"
        "• в расписании появляется новый показ — дата, время и ссылка;\n"
        "• на конкретный показ появляются свободные места (например, кто-то не оплатил бронь).\n\n"
        "Билеты я не покупаю и не бронирую.\n\n"
        "/status — что бот видит сейчас\n"
        "/unsubscribe — отключить уведомления\n"
        "/subscribe — включить снова\n\n"
        "Вы подписаны.",
        parse_mode=None,
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    mon = MONITOR.get('mosbilet')
    h = mon.health if mon else None

    async with async_session_maker() as session:
        st = (await session.execute(
            select(MonitoringState).where(MonitoringState.source == 'mosbilet'))).scalar_one_or_none()
        shows = (await session.execute(
            select(Show).where(Show.event_id == settings.MOSBILET_EVENT_ID, Show.is_listed == True)  # noqa: E712
            .order_by(Show.starts_at))).scalars().all()
        me = (await session.execute(select(User).where(User.chat_id == message.chat.id))).scalar_one_or_none()
        subs = (await session.execute(
            select(func.count()).select_from(User).where(User.is_subscribed == True))).scalar()  # noqa: E712

    now = now_msk().replace(tzinfo=None)
    shows = [s for s in shows if s.starts_at > now]
    lines = ["📊 Мосбилет, «Жирная Люба»", ""]

    last_check = h.last_check_at if h and h.last_check_at else (st.last_check if st else None)
    last_ok = h.last_ok_at if h and h.last_ok_at else (st.last_success if st else None)
    lines.append(f"Последняя проверка: {fmt_msk(last_check)} (МСК)")
    lines.append(f"Последняя успешная: {fmt_msk(last_ok)}")

    if h and h.consecutive_failures:
        lines.append(f"⚠️ Ошибок подряд: {h.consecutive_failures}. {h.last_error or ''}".strip())
    if h and h.consecutive_empty:
        lines.append(f"⚠️ Проверок подряд без найденных показов: {h.consecutive_empty} "
                     f"— возможно, сайт поменялся")
    if h and h.seats_source_ok is False:
        lines.append(f"⚠️ Билетная система не ответила {h.consecutive_seats_failures} "
                     f"{'проверку' if h.consecutive_seats_failures == 1 else 'проверок'} подряд — "
                     "новые показы вижу, места по показам сейчас нет")

    lines.append("")
    if shows:
        total = sum(s.free_seats or 0 for s in shows)
        lines.append(f"Найдено показов: {len(shows)}, свободных мест всего: {total}")
        for s in shows:
            seats = (f"{s.free_seats} {plural(s.free_seats, 'место', 'места', 'мест')}"
                     if s.free_seats else "мест нет")
            if s.free_seats and s.min_price:
                seats += f", от {s.min_price} ₽"
            lines.append(f"• {fmt_show(s.starts_at)} — {seats}")
    else:
        lines.append("Показов не найдено")

    if h:
        lines += ["", f"Проверок с запуска ({fmt_msk(h.started_at)}): {h.checks_total}, "
                      f"неудачных: {h.checks_failed}"]
    lines.append(f"Интервал: {settings.BASE_INTERVAL} с. Подписчиков: {subs}.")
    if me is not None:
        lines.append("Ваши уведомления: " + ("включены" if me.is_subscribed else "выключены"))
    lines += ["", settings.event_url]

    await message.answer("\n".join(lines), parse_mode=None, disable_web_page_preview=True)


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user = await get_or_create_user(message)
    if user.is_subscribed:
        await message.answer("✅ Вы уже подписаны на уведомления.", parse_mode=None)
        return
    async with async_session_maker() as session:
        await session.execute(update(User).where(User.chat_id == message.chat.id).values(is_subscribed=True))
        await session.commit()
    await message.answer("✅ Уведомления включены.", parse_mode=None)


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.chat_id == message.chat.id))
        user = res.scalar_one_or_none()
        if not user or not user.is_subscribed:
            await message.answer("Вы и так не подписаны.", parse_mode=None)
            return
        await session.execute(update(User).where(User.chat_id == message.chat.id).values(is_subscribed=False))
        await session.commit()
    await message.answer("❌ Уведомления отключены. /subscribe — включить снова.", parse_mode=None)
