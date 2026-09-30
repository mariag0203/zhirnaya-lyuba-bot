# Упаковать бота и отправить на сервер (запускать в PowerShell из папки бота).
# .env не отправляется: на сервере остаётся свой. Для самой первой установки скопируйте его вручную:
#   scp .env bloxa-home:~/zhirnaya-lyuba-bot/.env
#   cd $HOME\Desktop\zhirnaya-lyuba-bot ; powershell -ExecutionPolicy Bypass -File deploy\pack.ps1
$ErrorActionPreference = "Stop"
tar -czf "$env:TEMP\zl-bot.tgz" `
  --exclude=venv --exclude=.venv --exclude=__pycache__ --exclude=.git `
  --exclude="_backup_*" --exclude=.env --exclude="bot.log*" --exclude=bot.db --exclude="*.tgz" --exclude="*.bundle" `
  -C . .
scp "$env:TEMP\zl-bot.tgz" bloxa-home:/tmp/zl-bot.tgz
ssh -t bloxa-home "mkdir -p ~/zhirnaya-lyuba-bot && tar -xzf /tmp/zl-bot.tgz -C ~/zhirnaya-lyuba-bot && rm /tmp/zl-bot.tgz && cd ~/zhirnaya-lyuba-bot && bash deploy/install.sh"
