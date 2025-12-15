# ============================================================================
# Generate Secure Secrets for Docker Compose
# ============================================================================
# PowerShell script to generate random secure passwords

Write-Host "Generating secure secrets..." -ForegroundColor Cyan

# Create secrets directory
$secretsDir = ".\secrets"
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir | Out-Null
    Write-Host "[OK] Created secrets directory" -ForegroundColor Green
}

# Function to generate random password
function New-SecurePassword {
    param(
        [int]$Length = 32
    )
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $password = -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $password
}

# Generate secrets
$secrets = @{
    "db_password"            = New-SecurePassword -Length 32
    "redis_password"         = New-SecurePassword -Length 32
    "secret_key"             = New-SecurePassword -Length 64
    "admin_password"         = New-SecurePassword -Length 24
    "grafana_admin_password" = New-SecurePassword -Length 24
    "prometheus_password"    = New-SecurePassword -Length 24
    "backup_encryption_key"  = New-SecurePassword -Length 32
}

# Write secrets to files
foreach ($secret in $secrets.GetEnumerator()) {
    $filePath = Join-Path $secretsDir "$($secret.Key).txt"
    $secret.Value | Out-File -FilePath $filePath -NoNewline -Encoding ASCII
    
    # Set restrictive permissions (Windows)
    try {
        $acl = Get-Acl $filePath
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
            "FullControl",
            "Allow"
        )
        $acl.SetAccessRule($rule)
        Set-Acl $filePath $acl
    }
    catch {
        Write-Host "[WARN] Could not set file permissions: $_" -ForegroundColor Yellow
    }
    
    Write-Host "[OK] Generated: $($secret.Key)" -ForegroundColor Green
}

Write-Host ""
Write-Host "All secrets generated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Generated secrets:" -ForegroundColor Yellow
foreach ($secret in $secrets.GetEnumerator()) {
    Write-Host "   - $($secret.Key).txt" -ForegroundColor White
}
Write-Host ""
Write-Host "IMPORTANT: Keep these files secure and never commit to Git!" -ForegroundColor Red
Write-Host "   Add 'secrets/' to .gitignore" -ForegroundColor Yellow
Write-Host ""

# Update .gitignore
$gitignorePath = ".\.gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    if ($gitignoreContent -notmatch "secrets/") {
        Add-Content $gitignorePath "`n# Docker Secrets`nsecrets/`n*.txt"
        Write-Host "[OK] Updated .gitignore" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Admin Password: $($secrets['admin_password'])" -ForegroundColor Cyan
Write-Host "Grafana Password: $($secrets['grafana_admin_password'])" -ForegroundColor Cyan
Write-Host ""
Write-Host "Save these passwords in a secure password manager!" -ForegroundColor Yellow
