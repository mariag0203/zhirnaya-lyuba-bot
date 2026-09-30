#!/usr/bin/env bash
# Установка/обновление бота на сервере. Запускать из папки бота:
#   cd ~/zhirnaya-lyuba-bot && bash deploy/install.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=zhirnaya-lyuba-bot
RUN_USER="$(id -un)"

cd "$APP_DIR"
[ -f .env ] || { echo "Нет файла .env в $APP_DIR"; exit 1; }

# Файлы отключённых мониторов из прошлых версий (tar при обновлении их не удаляет)
rm -f monitors/afisha.py monitors/shalom_site.py monitors/telegram_channel.py \
      monitors/vk_group.py utils/proxy_pool.py

if ! python3 -c 'import venv, ensurepip' 2>/dev/null; then
  echo "Нужен пакет python3-venv: sudo apt install -y python3-venv"; exit 1
fi

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Быстрая проверка, что код импортируется и настройки читаются
.venv/bin/python -c "from config.settings import settings; settings.validate(); import main; print('OK, интервал', settings.BASE_INTERVAL, 'с, событие', settings.event_url)"

sudo tee /etc/systemd/system/$SERVICE.service >/dev/null <<UNIT
[Unit]
Description=Zhirnaya Lyuba ticket notifier (Mosbilet -> Telegram)
After=network-online.target
Wants=network-online.target
# перезапускать без ограничения числа попыток
StartLimitIntervalSec=0

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python main.py
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE
sudo systemctl restart $SERVICE
sleep 5
systemctl --no-pager status $SERVICE | head -15
echo
echo "Логи: journalctl -u $SERVICE -f"
