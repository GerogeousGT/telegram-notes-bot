# Синхронизация данных с VPS на локальный диск (rclone copy — файлы на сервере сохраняются для AI-поиска)
$RemoteName = "vps-bot"
$VpsBotPath = if ($env:VPS_BOT_PATH) { $env:VPS_BOT_PATH } else { "/home/deploy/bots/telegram-bot" }
$RemotePath = "$VpsBotPath/Распределение"
$LocalPath  = "$PSScriptRoot\Распределение"

Write-Host "== Синхронизация данных бота с VPS ==" -ForegroundColor Cyan

if (-not (Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath -Force | Out-Null
}

try {
    Write-Host "Копирование файлов с VPS на локальный диск..." -ForegroundColor Yellow
    $remoteSpec = "${RemoteName}:${RemotePath}"
    & rclone copy $remoteSpec "$LocalPath" --checksum
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Готово: данные скопированы на ПК. Файлы на VPS сохранены (нужны для AI-поиска)." -ForegroundColor Green
    } else {
        Write-Host "Ошибка при выполнении rclone copy (код $LASTEXITCODE)." -ForegroundColor Red
    }
} catch {
    Write-Host "Ошибка: rclone не найден или VPS недоступен." -ForegroundColor Red
}
