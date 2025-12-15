# ============================================
# Script de Geracao de Certificados SSL
# ============================================
# Gera certificados self-signed usando Docker + OpenSSL

Write-Host "Gerando Certificados SSL Self-Signed..." -ForegroundColor Cyan

$certsDir = ".\ssl\certs"
$privateDir = ".\ssl\private"

# Criar diretorios se nao existirem
New-Item -ItemType Directory -Force -Path $certsDir | Out-Null
New-Item -ItemType Directory -Force -Path $privateDir | Out-Null

Write-Host "Configurando certificado..." -ForegroundColor Green

# Configuracao do certificado
$domain = "localhost"
$ip = "192.168.15.3"
$days = 365

# Criar arquivo de configuracao OpenSSL
$configContent = @"
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
C = BR
ST = SP
L = Sao Paulo
O = Careca.ai
OU = Development
CN = $domain

[v3_req]
subjectAltName = @alt_names
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = $domain
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = $ip
"@

$configFile = ".\ssl\openssl.cnf"
Set-Content -Path $configFile -Value $configContent

Write-Host "Gerando certificado usando Docker + OpenSSL..." -ForegroundColor Green

# Usar Docker para rodar OpenSSL
$currentDir = (Get-Location).Path
docker run --rm `
    -v "${currentDir}/ssl:/ssl" `
    alpine/openssl req -x509 -nodes -days $days `
    -newkey rsa:2048 `
    -keyout /ssl/private/key.pem `
    -out /ssl/certs/cert.pem `
    -config /ssl/openssl.cnf

if ($LASTEXITCODE -eq 0) {
    Write-Host "Certificado SSL gerado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalhes do certificado:" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Gray
    Write-Host "Certificado: $certsDir\cert.pem" -ForegroundColor Cyan
    Write-Host "Chave Privada: $privateDir\key.pem" -ForegroundColor Cyan
    Write-Host "Dominio: $domain" -ForegroundColor Cyan
    Write-Host "IP: $ip" -ForegroundColor Cyan
    Write-Host "Validade: $days dias" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Gray
    Write-Host ""
    Write-Host "IMPORTANTE: Este e um certificado self-signed!" -ForegroundColor Yellow
    Write-Host "   Seu navegador mostrara um aviso de seguranca." -ForegroundColor Yellow
    Write-Host "   Para producao, use Let's Encrypt (certbot)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Acesse: https://localhost ou https://$ip" -ForegroundColor Green
    
    # Limpar arquivo de configuracao temporario
    Remove-Item $configFile -ErrorAction SilentlyContinue
}
else {
    Write-Host "Erro ao gerar certificado!" -ForegroundColor Red
    Write-Host "Certifique-se de que o Docker esta rodando." -ForegroundColor Yellow
    exit 1
}
