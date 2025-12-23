# Script para configurar IP estático 192.168.15.3
# Requer execução como Administrador

$interfaceAlias = "Ethernet"
$ipAddress = "192.168.15.3"
$prefixLength = 24
$gateway = "192.168.15.1"
$dnsServers = @("192.168.15.1")

Write-Host "Configurando IP estático..." -ForegroundColor Yellow

# Remove o IP atual
try {
    Remove-NetIPAddress -InterfaceAlias $interfaceAlias -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "IP anterior removido." -ForegroundColor Green
} catch {
    Write-Host "Aviso ao remover IP: $_" -ForegroundColor Yellow
}

# Remove gateway anterior
try {
    Remove-NetRoute -InterfaceAlias $interfaceAlias -DestinationPrefix "0.0.0.0/0" -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Gateway anterior removido." -ForegroundColor Green
} catch {
    Write-Host "Aviso ao remover gateway: $_" -ForegroundColor Yellow
}

# Configura novo IP
try {
    New-NetIPAddress -InterfaceAlias $interfaceAlias -IPAddress $ipAddress -PrefixLength $prefixLength -DefaultGateway $gateway
    Write-Host "Novo IP configurado: $ipAddress" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar IP: $_" -ForegroundColor Red
    exit 1
}

# Configura DNS
try {
    Set-DnsClientServerAddress -InterfaceAlias $interfaceAlias -ServerAddresses $dnsServers
    Write-Host "DNS configurado: $dnsServers" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar DNS: $_" -ForegroundColor Red
}

# Verifica configuração final
Write-Host "`nConfiguracao atual:" -ForegroundColor Cyan
Get-NetIPAddress -InterfaceAlias $interfaceAlias -AddressFamily IPv4 | Select-Object IPAddress, PrefixLength
Get-NetRoute -InterfaceAlias $interfaceAlias -DestinationPrefix "0.0.0.0/0" | Select-Object NextHop
Get-DnsClientServerAddress -InterfaceAlias $interfaceAlias -AddressFamily IPv4 | Select-Object ServerAddresses

Write-Host "`nConfiguração concluída com sucesso!" -ForegroundColor Green
