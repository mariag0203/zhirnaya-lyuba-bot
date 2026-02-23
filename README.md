# Zhirnaya Lyuba Bot

Telegram-бот для мониторинга появления билетов на спектакль.

## Источники мониторинга

- Официальный сайт Театра «Шалом»
- Afisha.ru
- bilet.mos.ru
- Telegram-канал театра
- Группа ВКонтакте

## Установка

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

```bash
cp .env.example .env
# Заполните .env своими значениями
```

### Получение токенов

| Переменная | Где получить |
|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `ADMIN_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) |
| `TG_API_ID` / `TG_API_HASH` | [my.telegram.org](https://my.telegram.org) |
| `VK_TOKEN` | [vk.com/dev](https://vk.com/dev) → Standalone-приложение |

## Запуск

```bash
python main.py
```

## Структура проекта

```
zhirnaya-lyuba-bot/
├── config/         # Настройки и переменные окружения
├── bot/            # Обработчики бота и уведомления
├── monitors/       # Мониторы источников билетов
├── database/       # Модели и подключение к БД
├── utils/          # Прокси-пул и планировщик
└── main.py         # Точка входа
```

## Режимы мониторинга

- **Нормальный**: проверка каждые `BASE_INTERVAL` секунд (по умолчанию 60)
- **Усиленный**: при обнаружении билетов переключается на `ENHANCED_INTERVAL` секунд (по умолчанию 2) на `ENHANCED_DURATION` секунд (по умолчанию 900)
