# Перезапуск бота на VPS
# VPS-параметры берутся из переменной или заданы явно
$SshHost = $env:VPS_HOST ?? "205.172.56.149"
$User    = $env:VPS_USER ?? "deploy"
$Path    = $env:VPS_BOT_PATH ?? "/home/deploy/bots/telegram-bot"

Write-Host "Перезапуск бота на $User@$SshHost..." -ForegroundColor Cyan
$cmd = "cd $Path; pkill -f 'python.*bot.py' 2>/dev/null; sleep 1; nohup python3 bot.py >> bot.log 2>&1 &; echo 'Бот перезапущен'"
ssh "${User}@${SshHost}" $cmd
