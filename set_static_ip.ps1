# Script para definir IP estático 192.168.15.3
# ATENÇÃO: Execute este script como Administrador (Botão direito -> Executar com o PowerShell como Admin)

$InterfaceAlias = "Ethernet"
$IP = "192.168.15.3"
$Gateway = "192.168.15.1"
$Prefix = 24
$DNS = "1.1.1.1", "8.8.8.8"

Write-Host "Configurando IP Estático ($IP) na interface '$InterfaceAlias'..." -ForegroundColor Cyan

# Verifica Privilegios
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Este script precisa ser executado como Administrador!"
    Write-Host "Pressione qualquer tecla para sair..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

try {
    # Tenta definir o endereço. 
    # Estratégia segura: Desabilitar DHCP primeiro torna a interface estática.
    
    Write-Host "Desabilitando DHCP..."
    Set-NetIPInterface -InterfaceAlias $InterfaceAlias -Dhcp Disabled
    
    # Remove endereços IP anteriores (para garantir limpeza, caso haja lixo de configuração)
    Remove-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    
    # Adiciona o novo IP
    Write-Host "Definindo IP e Gateway..."
    New-NetIPAddress -InterfaceAlias $InterfaceAlias -IPAddress $IP -PrefixLength $Prefix -DefaultGateway $Gateway
    
    # Configura DNS
    Write-Host "Configurando DNS..."
    Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ServerAddresses $DNS
    
    Write-Host "Configuração realizada com sucesso!" -ForegroundColor Green
    Get-NetIPConfiguration -InterfaceAlias $InterfaceAlias
}
catch {
    Write-Error "Ocorreu um erro: $_"
    Write-Host "Tentando restaurar DHCP por segurança..." -ForegroundColor Yellow
    Set-NetIPInterface -InterfaceAlias $InterfaceAlias -Dhcp Enabled
    Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ResetServerAddresses
}

Write-Host "Pressione qualquer tecla para fechar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
