# Script para limpar resíduos do Docker no C:
# Execute como Administrador

Write-Host "=== Limpando resíduos do Docker no C: ===" -ForegroundColor Cyan

# 1. Parar Docker Desktop
Write-Host "`n1. Parando Docker Desktop..." -ForegroundColor Yellow
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5

# 2. Parar serviços
Write-Host "2. Parando serviços Docker..." -ForegroundColor Yellow
Stop-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue
wsl --shutdown
Start-Sleep -Seconds 3

# 3. Verificar tamanho antes
Write-Host "`n3. Verificando tamanho atual..." -ForegroundColor Yellow
$dockerLocal = "C:\Users\$env:USERNAME\AppData\Local\Docker"
if (Test-Path $dockerLocal) {
    $sizeBefore = (Get-ChildItem $dockerLocal -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "   Tamanho atual: $([math]::Round($sizeBefore, 2)) GB" -ForegroundColor Red
}

# 4. Remover diretórios antigos
Write-Host "`n4. Removendo diretórios antigos do Docker..." -ForegroundColor Yellow

$pathsToRemove = @(
    "C:\Users\$env:USERNAME\AppData\Local\Docker\wsl",
    "C:\Users\$env:USERNAME\AppData\Local\Docker\windowsfilter",
    "C:\ProgramData\DockerDesktop",
    "C:\Users\$env:USERNAME\.docker"
)

foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        Write-Host "   Removendo: $path" -ForegroundColor Gray
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 5. Limpar cache WSL antigo
Write-Host "`n5. Limpando cache WSL..." -ForegroundColor Yellow
$wslPath = "C:\Users\$env:USERNAME\AppData\Local\Packages\CanonicalGroupLimited*"
Get-Item $wslPath -ErrorAction SilentlyContinue | ForEach-Object {
    $localState = Join-Path $_.FullName "LocalState"
    if (Test-Path $localState) {
        Get-ChildItem $localState -Filter "ext4.vhdx" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "   Compactando: $($_.FullName)" -ForegroundColor Gray
            Optimize-VHD -Path $_.FullName -Mode Full -ErrorAction SilentlyContinue
        }
    }
}

# 6. Verificar tamanho depois
Write-Host "`n6. Verificando espaço liberado..." -ForegroundColor Yellow
if (Test-Path $dockerLocal) {
    $sizeAfter = (Get-ChildItem $dockerLocal -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB
    $freed = $sizeBefore - $sizeAfter
    Write-Host "   Tamanho atual: $([math]::Round($sizeAfter, 2)) GB" -ForegroundColor Green
    Write-Host "   Espaço liberado: $([math]::Round($freed, 2)) GB" -ForegroundColor Green
}

Write-Host "`n=== Concluído! ===" -ForegroundColor Green
Write-Host "Agora você pode iniciar o Docker Desktop." -ForegroundColor Cyan
Write-Host "`nSe ainda houver arquivos em C:\Users\$env:USERNAME\AppData\Local\Docker," -ForegroundColor Yellow
Write-Host "você pode deletá-los manualmente após confirmar que o Docker funciona no D:" -ForegroundColor Yellow
