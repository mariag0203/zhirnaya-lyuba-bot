"""
Система уведомлений - отправка сообщений пользователям
"""

from aiogram import Bot
from sqlalchemy import select
from database.models import User, NotificationLog, TicketEvent
from database.db import async_session_maker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def broadcast(
    bot: Bot,
    message: str,
    notification_type: str = "info",
    event_id: int = None,
    parse_mode: str = "Markdown"
) -> int:
    """
    Рассылка сообщения всем подписанным пользователям

    Args:
        bot: Экземпляр aiogram Bot
        message: Текст сообщения
        notification_type: Тип уведомления (new_sale, returned_tickets, announcement)
        event_id: ID события из TicketEvent (если применимо)
        parse_mode: Режим парсинга (Markdown/HTML)

    Returns:
        Количество успешно отправленных сообщений
    """
    async with async_session_maker() as session:
        # Получаем всех подписанных пользователей
        result = await session.execute(
            select(User).where(User.is_subscribed == True)
        )
        users = result.scalars().all()

        success_count = 0
        failed_users = []

        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                success_count += 1
                logger.info(f"✓ Уведомление отправлено: {user.chat_id}")
            except Exception as e:
                failed_users.append(user.chat_id)
                logger.error(f"✗ Ошибка отправки {user.chat_id}: {e}")

        # Логируем результат рассылки
        log_entry = NotificationLog(
            event_id=event_id,
            notification_type=notification_type,
            message=message,
            recipients_count=success_count,
            sent_at=datetime.utcnow(),
            success=(len(failed_users) == 0),
            error_text=f"Failed for: {failed_users}" if failed_users else None
        )
        session.add(log_entry)
        await session.commit()

        logger.info(f"📨 Рассылка завершена: {success_count}/{len(users)} успешно")
        return success_count


async def notify_tickets_found(
    bot: Bot,
    event_date: str,
    venue: str,
    links: dict
) -> int:
    """
    Уведомление об открытии продаж билетов

    Args:
        bot: Экземпляр aiogram Bot
        event_date: Дата спектакля (строка, например "06 марта, 19:00")
        venue: Площадка
        links: Словарь со ссылками {source: url}

    Returns:
        Количество отправленных уведомлений
    """
    message_lines = [
        "🚨 **СТАРТ ПРОДАЖ!** 🚨",
        "",
        "**Спектакль:** Жирная Люба",
        f"**Дата:** {event_date}",
        f"**Площадка:** {venue}",
        "",
        "**Ссылки на покупку (КЛИКАЙ БЫСТРО):**"
    ]

    # Добавляем ссылки из разных источников
    source_names = {
        'shalom_site': '🎭 Офиц. сайт',
        'afisha': '🎫 Afisha',
        'mosbilet': '🏛 Мосбилет'
    }

    for source, url in links.items():
        name = source_names.get(source, source)
        message_lines.append(f"{name}: {url}")

    message = "\n".join(message_lines)

    return await broadcast(
        bot=bot,
        message=message,
        notification_type="new_sale"
    )


async def notify_returned_tickets(
    bot: Bot,
    event_date: str,
    venue: str,
    source: str,
    url: str
) -> int:
    """
    Уведомление о возвращенных билетах

    Args:
        bot: Экземпляр aiogram Bot
        event_date: Дата спектакля
        venue: Площадка
        source: Источник (shalom_site, afisha, mosbilet)
        url: Ссылка на покупку

    Returns:
        Количество отправленных уведомлений
    """
    source_names = {
        'shalom_site': 'Офиц. сайт',
        'afisha': 'Afisha.ru',
        'mosbilet': 'Мосбилет'
    }
    source_name = source_names.get(source, source)

    message = f"""
🔄 **ОСВОБОДИЛИСЬ БИЛЕТЫ!**

**Спектакль:** Жирная Люба
**Дата:** {event_date}
**Площадка:** {venue}

Кто-то не оплатил бронь, билеты вернулись в продажу!

**Источник:** {source_name}
**Ссылка:** {url}
    """.strip()

    return await broadcast(
        bot=bot,
        message=message,
        notification_type="returned_tickets"
    )


async def notify_announcement(
    bot: Bot,
    announcement_text: str,
    source: str,
    source_url: str
) -> int:
    """
    Уведомление об анонсе от театра

    Args:
        bot: Экземпляр aiogram Bot
        announcement_text: Текст анонса
        source: Источник (telegram, vk, website)
        source_url: Ссылка на пост/новость

    Returns:
        Количество отправленных уведомлений
    """
    source_names = {
        'telegram': '📱 Telegram-канал',
        'vk': '💬 VK группа',
        'website': '🌐 Сайт театра'
    }
    source_name = source_names.get(source, source)

    message = f"""
📢 **АНОНС ОТ ТЕАТРА**

**Источник:** {source_name}

{announcement_text}

**Оригинал:** {source_url}
    """.strip()

    return await broadcast(
        bot=bot,
        message=message,
        notification_type="announcement"
    )


async def notify_admin(
    bot: Bot,
    admin_chat_id: int,
    message: str
) -> bool:
    """
    Отправка уведомления администратору (для отладки/ошибок)

    Args:
        bot: Экземпляр aiogram Bot
        admin_chat_id: Chat ID администратора
        message: Текст сообщения

    Returns:
        True если отправлено успешно
    """
    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=f"🔧 **ADMIN NOTIFICATION**\n\n{message}",
            parse_mode="Markdown"
        )
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка отправки админу: {e}")
        return False
