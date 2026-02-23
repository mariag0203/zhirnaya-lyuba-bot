# 🎭 Telegram-бот для мониторинга билетов "Жирная Люба"

Бот для автоматического отслеживания появления билетов на спектакль "Жирная Люба" театра "Шалом" на официальных площадках продаж.

## 🎯 Возможности

- ⚡ **Быстрое обнаружение** - уведомление в течение 1-2 секунд после открытия продаж
- 🔍 **Мониторинг нескольких источников**:
  - Официальный сайт театра (shalom-theatre.ru)
  - Afisha.ru
  - Мосбилет (bilet.mos.ru)
  - Telegram-канал театра (опционально)
  - VK группа театра (опционально)
- 🔄 **Отслеживание возвратов** - уведомления о билетах, вернувшихся в продажу
- 🚀 **Умные режимы** - переключение между обычным и усиленным мониторингом
- 🔐 **Поддержка прокси** - ротация IP для стабильной работы

## 📋 Требования

- Python 3.9+
- Telegram Bot Token (от [@BotFather](https://t.me/botfather))
- SQLite (встроен в Python)

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/mariag0203/zhirnaya-lyuba-bot.git
cd zhirnaya-lyuba-bot
```

### 2. Создание виртуального окружения
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Скопируйте `.env.example` в `.env` и заполните:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
# Обязательные параметры
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_CHAT_ID=your_telegram_chat_id

# Опциональные параметры
VK_TOKEN=your_vk_token
TG_API_ID=your_telegram_api_id
TG_API_HASH=your_telegram_api_hash
TG_PHONE=your_phone_number

# Прокси (если нужно)
PROXY_LIST=http://proxy1:port,http://proxy2:port
```

### 5. Запуск бота
```bash
python main.py
```

## 🔧 Получение токенов и ID

### Telegram Bot Token

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

### Chat ID

1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте любое сообщение
3. Скопируйте ваш ID

### VK Token (опционально)

1. Перейдите на [vk.com/apps?act=manage](https://vk.com/apps?act=manage)
2. Создайте Standalone-приложение
3. Получите сервисный ключ доступа

### Telegram API (опционально)

1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Войдите со своим номером телефона
3. Создайте приложение в разделе "API development tools"
4. Скопируйте `api_id` и `api_hash`

## 📱 Команды бота

- `/start` - Приветствие и описание работы
- `/status` - Текущий статус мониторинга
- `/subscribe` - Включить уведомления
- `/unsubscribe` - Отключить уведомления

## 🏗️ Архитектура проекта

```
zhirnaya-lyuba-bot/
├── config/
│   └── settings.py          # Конфигурация приложения
├── bot/
│   ├── handlers.py          # Обработчики команд
│   └── notifications.py     # Система рассылки уведомлений
├── monitors/
│   ├── base_monitor.py      # Базовый класс мониторинга
│   ├── shalom_site.py       # Мониторинг сайта театра
│   ├── afisha.py            # Мониторинг Afisha.ru
│   ├── mosbilet.py          # Мониторинг bilet.mos.ru
│   ├── telegram_channel.py  # Мониторинг Telegram-канала
│   └── vk_group.py          # Мониторинг VK группы
├── database/
│   ├── models.py            # Модели БД (SQLAlchemy)
│   └── db.py                # Подключение и сессии
├── utils/
│   ├── proxy_pool.py        # Управление прокси
│   └── scheduler.py         # Планировщик мониторов
├── .env.example             # Шаблон конфигурации
├── requirements.txt         # Зависимости Python
└── main.py                  # Точка входа
```

## ⚙️ Настройка интервалов мониторинга

В файле `.env`:
```env
# Обычный режим (секунды)
BASE_INTERVAL=60

# Усиленный режим (секунды)
ENHANCED_INTERVAL=2

# Длительность усиленного режима (секунды)
ENHANCED_DURATION=900
```

## 🔐 Настройка прокси

Добавьте список прокси в `.env`:
```env
PROXY_LIST=http://user:pass@proxy1.com:8080,http://user:pass@proxy2.com:8080
```

Формат поддерживаемых прокси: HTTP/HTTPS

## 📊 Логирование

Логи записываются в:
- Консоль (stdout)
- Файл `bot.log`

Уровень логирования: INFO

## ⚠️ Важные замечания

1. **Бот НЕ покупает билеты** - только уведомляет о их появлении
2. **Работает с публичными API** - не использует обход защиты
3. **Соблюдает rate limits** - не создает избыточную нагрузку на сайты
4. **Этично** - не мешает обычным покупателям

## 🐛 Troubleshooting

### Ошибка: "BOT_TOKEN не задан"
Проверьте файл `.env` и убедитесь, что токен указан корректно.

### Мониторы не запускаются
Проверьте логи в `bot.log` - возможно проблемы с доступом к сайтам или прокси.

### База данных не создается
Убедитесь, что у приложения есть права на запись в текущую директорию.

## 📝 Лицензия

MIT License - свободное использование с указанием авторства.

## 🤝 Вклад в проект

Pull requests приветствуются! Для крупных изменений сначала откройте issue.

## 📧 Контакты

GitHub: [@mariag0203](https://github.com/mariag0203)
