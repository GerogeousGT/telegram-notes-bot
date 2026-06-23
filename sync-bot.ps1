# Синхронизация данных с VPS на локальный диск (rclone move)
$RemoteName = "vps-bot"
$RemotePath = ($env:VPS_BOT_PATH ?? "/home/deploy/bots/telegram-bot") + "/Распределение"
$LocalPath  = "$PSScriptRoot\Распределение"

Write-Host "== Синхронизация данных бота с VPS ==" -ForegroundColor Cyan

if (-not (Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath -Force | Out-Null
}

try {
    Write-Host "Перенос файлов с VPS на локальный диск..." -ForegroundColor Yellow
    $remoteSpec = "${RemoteName}:${RemotePath}"
    & rclone move $remoteSpec "$LocalPath" --checksum
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Готово: данные бота перенесены на ПК, с VPS удалены." -ForegroundColor Green
    } else {
        Write-Host "Ошибка при выполнении rclone move (код $LASTEXITCODE)." -ForegroundColor Red
    }
} catch {
    Write-Host "Ошибка: rclone не найден или VPS недоступен." -ForegroundColor Red
}
