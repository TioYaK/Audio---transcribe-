# ============================================================================
# Update .env for Security Hardened Configuration
# ============================================================================

Write-Host "Updating .env file for secure deployment..." -ForegroundColor Cyan

$envFile = ".\.env"
$envBackup = ".\.env.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# Backup existing .env
if (Test-Path $envFile) {
    Copy-Item $envFile $envBackup
    Write-Host "[OK] Backed up .env to $envBackup" -ForegroundColor Green
}

# Read current .env
$envContent = @()
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
}

# Remove old secret-related variables
$envContent = $envContent | Where-Object {
    $_ -notmatch "^DB_PASSWORD=" -and
    $_ -notmatch "^REDIS_PASSWORD=" -and
    $_ -notmatch "^SECRET_KEY=" -and
    $_ -notmatch "^ADMIN_PASSWORD=" -and
    $_ -notmatch "^GRAFANA_PASSWORD="
}

# Add new configuration if not present
$newVars = @{
    "DB_USER"       = "careca"
    "DB_NAME"       = "carecadb"
    "DB_HOST"       = "db"
    "DB_PORT"       = "5432"
    "REDIS_HOST"    = "redis"
    "REDIS_PORT"    = "6379"
    "REDIS_DB"      = "0"
    "HOST_USER_ID"  = "1000"
    "HOST_GROUP_ID" = "1000"
}

foreach ($var in $newVars.GetEnumerator()) {
    $pattern = "^$($var.Key)="
    $exists = $envContent | Where-Object { $_ -match $pattern }
    
    if (-not $exists) {
        $envContent += "$($var.Key)=$($var.Value)"
        Write-Host "[ADD] $($var.Key)=$($var.Value)" -ForegroundColor Green
    }
    else {
        Write-Host "[SKIP] $($var.Key) already exists" -ForegroundColor Yellow
    }
}

# Add comment about secrets
$secretComment = @"

# ============================================================================
# SECURITY: Passwords now managed via Docker Secrets
# ============================================================================
# The following are NO LONGER needed (removed for security):
# - DB_PASSWORD (now in secrets/db_password.txt)
# - REDIS_PASSWORD (now in secrets/redis_password.txt)
# - SECRET_KEY (now in secrets/secret_key.txt)
# - ADMIN_PASSWORD (now in secrets/admin_password.txt)
# ============================================================================
"@

if ($envContent -notmatch "Docker Secrets") {
    $envContent += $secretComment
}

# Write updated .env
$envContent | Out-File -FilePath $envFile -Encoding UTF8

Write-Host ""
Write-Host "[OK] .env file updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Changes made:" -ForegroundColor Yellow
Write-Host "  - Removed: DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY, ADMIN_PASSWORD" -ForegroundColor Red
Write-Host "  - Added: DB_USER, DB_NAME, DB_HOST, DB_PORT" -ForegroundColor Green
Write-Host "  - Added: REDIS_HOST, REDIS_PORT, REDIS_DB" -ForegroundColor Green
Write-Host "  - Added: HOST_USER_ID, HOST_GROUP_ID" -ForegroundColor Green
Write-Host ""
Write-Host "Backup saved to: $envBackup" -ForegroundColor Cyan
