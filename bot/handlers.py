"""
Обработчики команд Telegram-бота
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, MonitoringState
from database.db import async_session_maker
from config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = Router()


async def get_or_create_user(message: Message) -> User:
    """Получить или создать пользователя в БД"""
    async with async_session_maker() as session:
        # Проверяем существование пользователя
        result = await session.execute(
            select(User).where(User.chat_id == message.chat.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Создаем нового пользователя
            user = User(
                chat_id=message.chat.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                is_subscribed=True
            )
            session.add(user)
            await session.commit()
            logger.info(f"✓ Новый пользователь: {message.chat.id} (@{message.from_user.username})")

        return user


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start - приветствие и объяснение работы бота"""
    user = await get_or_create_user(message)

    welcome_text = f"""
👋 Привет, {message.from_user.first_name}!

Я бот-помощник для мониторинга билетов на спектакль **"Жирная Люба"** театра "Шалом".

🎭 **Что я делаю:**
- Отслеживаю официальные площадки продаж (сайт театра, Afisha.ru, Мосбилет)
- Мгновенно уведомляю о начале продаж билетов
- Присылаю прямые ссылки на покупку
- Отслеживаю возвращенные билеты

⚠️ **Что я НЕ делаю:**
- Не покупаю билеты автоматически
- Не резервирую места
- Не гарантирую 100% успех покупки

📊 **Мои команды:**
/status - статус мониторинга
/subscribe - включить уведомления
/unsubscribe - отключить уведомления

✅ Вы подписаны на уведомления!
Как только появятся билеты — я сразу сообщу.
    """.strip()

    await message.answer(welcome_text)


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Команда /status - показать статус мониторинга"""
    async with async_session_maker() as session:
        # Получаем состояние всех мониторов
        result = await session.execute(select(MonitoringState))
        monitors = result.scalars().all()

        # Получаем информацию о пользователе
        user_result = await session.execute(
            select(User).where(User.chat_id == message.chat.id)
        )
        user = user_result.scalar_one_or_none()

    if not monitors:
        status_text = "⚠️ Мониторинг еще не запущен"
    else:
        status_lines = ["📊 **Статус мониторинга:**\n"]

        source_names = {
            'shalom_site': '🎭 Сайт театра',
            'afisha': '🎫 Afisha.ru',
            'mosbilet': '🏛 Мосбилет',
            'telegram': '📱 Telegram-канал',
            'vk': '💬 VK группа'
        }

        for monitor in monitors:
            name = source_names.get(monitor.source, monitor.source)
            mode_emoji = "🔥" if monitor.mode == "enhanced" else "🟢"

            if monitor.last_success:
                time_str = monitor.last_success.strftime("%H:%M:%S")
                status_lines.append(f"{mode_emoji} {name}: ✓ ({time_str})")
            else:
                status_lines.append(f"⚪️ {name}: ожидание...")

        status_text = "\n".join(status_lines)

        # Добавляем информацию о подписке
        if user:
            sub_status = "✅ Включены" if user.is_subscribed else "❌ Отключены"
            status_text += f"\n\n**Уведомления:** {sub_status}"

        status_text += f"\n\n{settings.get_info()}"

    await message.answer(status_text)


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Команда /subscribe - включить уведомления"""
    user = await get_or_create_user(message)

    if user.is_subscribed:
        await message.answer("✅ Вы уже подписаны на уведомления!")
    else:
        async with async_session_maker() as session:
            await session.execute(
                update(User)
                .where(User.chat_id == message.chat.id)
                .values(is_subscribed=True)
            )
            await session.commit()
        await message.answer("✅ Уведомления включены! Я сообщу, когда появятся билеты.")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    """Команда /unsubscribe - отключить уведомления"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.chat_id == message.chat.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_subscribed:
            await message.answer("❌ Вы и так не подписаны на уведомления")
        else:
            await session.execute(
                update(User)
                .where(User.chat_id == message.chat.id)
                .values(is_subscribed=False)
            )
            await session.commit()
            await message.answer("❌ Уведомления отключены")
