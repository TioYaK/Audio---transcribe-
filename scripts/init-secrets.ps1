# ============================================
# Script de Inicializacao de Secrets
# ============================================
# Este script gera secrets seguros para o Docker Compose

Write-Host "Inicializando Docker Secrets..." -ForegroundColor Cyan

$secretsDir = ".\secrets"

# Funcao para gerar senha aleatoria
function New-SecurePassword {
    param([int]$Length = 32)
    $bytes = New-Object byte[] $Length
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).Substring(0, $Length)
}

# Funcao para gerar hex token
function New-HexToken {
    param([int]$Length = 64)
    $bytes = New-Object byte[] ($Length / 2)
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ''
}

# Verificar se secrets ja existem
if (Test-Path "$secretsDir\db_password.txt") {
    Write-Host "Secrets ja existem. Deseja sobrescrever? (s/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne 's' -and $response -ne 'S') {
        Write-Host "Operacao cancelada." -ForegroundColor Red
        exit 0
    }
}

# Criar diretorio se nao existir
New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null

Write-Host "Gerando secrets..." -ForegroundColor Green

# Gerar secrets
$dbPassword = New-SecurePassword -Length 32
$adminPassword = New-SecurePassword -Length 24
$secretKey = New-HexToken -Length 64
$redisPassword = New-SecurePassword -Length 32
$backupPassphrase = New-SecurePassword -Length 32

# Salvar secrets em arquivos
Set-Content -Path "$secretsDir\db_password.txt" -Value $dbPassword -NoNewline
Set-Content -Path "$secretsDir\admin_password.txt" -Value $adminPassword -NoNewline
Set-Content -Path "$secretsDir\secret_key.txt" -Value $secretKey -NoNewline
Set-Content -Path "$secretsDir\redis_password.txt" -Value $redisPassword -NoNewline
Set-Content -Path "$secretsDir\backup_passphrase.txt" -Value $backupPassphrase -NoNewline

Write-Host "Secrets gerados com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANTE: Anote estas credenciais em local seguro:" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Gray
Write-Host "Admin Password: $adminPassword" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Gray
Write-Host ""
Write-Host "Os secrets foram salvos em: $secretsDir" -ForegroundColor Green
Write-Host "NAO commite o diretorio 'secrets' no Git!" -ForegroundColor Red
Write-Host ""

# Atualizar .env
Write-Host "Atualizando .env..." -ForegroundColor Green

if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    
    # Atualizar ou adicionar variaveis
    if ($envContent -match "DB_PASSWORD=") {
        $envContent = $envContent -replace "DB_PASSWORD=.*", "DB_PASSWORD=$dbPassword"
    }
    else {
        $envContent += "`nDB_PASSWORD=$dbPassword"
    }
    
    if ($envContent -match "ADMIN_PASSWORD=") {
        $envContent = $envContent -replace "ADMIN_PASSWORD=.*", "ADMIN_PASSWORD=$adminPassword"
    }
    else {
        $envContent += "`nADMIN_PASSWORD=$adminPassword"
    }
    
    if ($envContent -match "SECRET_KEY=") {
        $envContent = $envContent -replace "SECRET_KEY=.*", "SECRET_KEY=$secretKey"
    }
    else {
        $envContent += "`nSECRET_KEY=$secretKey"
    }
    
    if ($envContent -match "REDIS_PASSWORD=") {
        $envContent = $envContent -replace "REDIS_PASSWORD=.*", "REDIS_PASSWORD=$redisPassword"
    }
    else {
        $envContent += "`nREDIS_PASSWORD=$redisPassword"
    }
    
    Set-Content -Path ".env" -Value $envContent
    Write-Host ".env atualizado!" -ForegroundColor Green
}
else {
    Write-Host "Arquivo .env nao encontrado. Copie .env.example para .env primeiro." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Configuracao completa! Execute: docker compose up -d" -ForegroundColor Green
