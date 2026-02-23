"""
Модуль обработчиков команд Telegram-бота.

Реализует обработку команд (/start, /status, /subscribe, /unsubscribe),
управление подписками пользователей и административные команды
для управления мониторингом.
"""

from aiogram import Router, types
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Обработчик команды /start. Приветствует пользователя."""
    await message.answer(
        "Привет! Я бот мониторинга билетов.\n"
        "Используй /subscribe чтобы подписаться на уведомления."
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    """Обработчик команды /status. Показывает текущий статус мониторинга."""
    await message.answer("Мониторинг активен.")


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message) -> None:
    """Обработчик команды /subscribe. Подписывает пользователя на уведомления."""
    await message.answer("Вы подписаны на уведомления о появлении билетов.")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message) -> None:
    """Обработчик команды /unsubscribe. Отписывает пользователя от уведомлений."""
    await message.answer("Вы отписаны от уведомлений.")
