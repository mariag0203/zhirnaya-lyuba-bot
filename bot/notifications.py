"""
Модуль отправки уведомлений пользователям.

Отвечает за формирование и рассылку уведомлений о появлении билетов
подписанным пользователям и администраторам. Поддерживает отправку
одиночных сообщений и массовую рассылку.
"""

from aiogram import Bot
from config.settings import ADMIN_CHAT_ID


async def notify_admin(bot: Bot, text: str) -> None:
    """Отправляет уведомление администратору."""
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)


async def broadcast(bot: Bot, user_ids: list[int], text: str) -> None:
    """
    Рассылает уведомление списку пользователей.

    Args:
        bot: Экземпляр бота aiogram.
        user_ids: Список Telegram ID пользователей.
        text: Текст уведомления.
    """
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except Exception:
            pass


async def notify_tickets_found(bot: Bot, user_ids: list[int], source: str, url: str) -> None:
    """
    Отправляет уведомление о появлении билетов.

    Args:
        bot: Экземпляр бота aiogram.
        user_ids: Список подписанных пользователей.
        source: Название источника (сайт, Afisha, и т.д.).
        url: Прямая ссылка на билеты.
    """
    text = f"Билеты появились!\n\nИсточник: {source}\nСсылка: {url}"
    await broadcast(bot, user_ids, text)
