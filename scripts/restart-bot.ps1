# Перезапуск бота на VPS
# VPS-параметры берутся из переменной или заданы явно
$SshHost = if ($env:VPS_HOST)    { $env:VPS_HOST }    else { "205.172.56.149" }
$User    = if ($env:VPS_USER)    { $env:VPS_USER }    else { "deploy" }
$Path    = if ($env:VPS_BOT_PATH){ $env:VPS_BOT_PATH } else { "/home/deploy/bots/telegram-bot" }

Write-Host "Перезапуск бота на $User@$SshHost..." -ForegroundColor Cyan
$cmd = "cd $Path; pkill -f 'python.*bot.py' 2>/dev/null; sleep 1; nohup python3 bot.py >> bot.log 2>&1 &; echo 'Бот перезапущен'"
ssh "${User}@${SshHost}" $cmd
