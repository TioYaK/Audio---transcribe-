# Script para mover Docker Desktop do C: para D:
# Execute como Administrador

Write-Host "=== Movendo Docker Desktop para D: ===" -ForegroundColor Cyan

# 1. Parar Docker Desktop
Write-Host "`n1. Parando Docker Desktop..." -ForegroundColor Yellow
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5

# 2. Parar serviços
Write-Host "2. Parando serviços Docker..." -ForegroundColor Yellow
Stop-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue
wsl --shutdown

# 3. Criar diretório de destino
Write-Host "3. Criando diretório D:\Docker..." -ForegroundColor Yellow
New-Item -Path "D:\Docker" -ItemType Directory -Force | Out-Null

# 4. Exportar WSL distro
Write-Host "4. Exportando docker-desktop-data..." -ForegroundColor Yellow
wsl --export docker-desktop-data "D:\Docker\docker-desktop-data.tar"

Write-Host "5. Exportando docker-desktop..." -ForegroundColor Yellow
wsl --export docker-desktop "D:\Docker\docker-desktop.tar"

# 5. Desregistrar WSL distros antigas
Write-Host "6. Removendo distros antigas..." -ForegroundColor Yellow
wsl --unregister docker-desktop-data
wsl --unregister docker-desktop

# 6. Importar para novo local
Write-Host "7. Importando docker-desktop-data para D:\Docker..." -ForegroundColor Yellow
wsl --import docker-desktop-data "D:\Docker\data" "D:\Docker\docker-desktop-data.tar" --version 2

Write-Host "8. Importando docker-desktop para D:\Docker..." -ForegroundColor Yellow
wsl --import docker-desktop "D:\Docker\distro" "D:\Docker\docker-desktop.tar" --version 2

# 7. Limpar arquivos temporários
Write-Host "9. Limpando arquivos temporários..." -ForegroundColor Yellow
Remove-Item "D:\Docker\docker-desktop-data.tar" -Force
Remove-Item "D:\Docker\docker-desktop.tar" -Force

Write-Host "`n=== Concluído! ===" -ForegroundColor Green
Write-Host "Agora inicie o Docker Desktop manualmente." -ForegroundColor Cyan
Write-Host "O Docker agora está em D:\Docker" -ForegroundColor Cyan
