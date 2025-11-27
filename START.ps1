# Simple reliable startup script
# Handles paths with spaces correctly

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting Application" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Get the directory where this script is located
$projectRoot = $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"

Write-Host "Project: $projectRoot" -ForegroundColor Gray
Write-Host ""

# Stop any existing processes first
Write-Host "Stopping any existing servers..." -ForegroundColor Yellow

# Stop Node/Vite processes (Frontend)
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like "*Vite*" -or $_.CommandLine -like "*vite*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop Python/uvicorn processes (Backend)
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*run_server*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill by port if still running
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Stop-Process -Id $port8000.OwningProcess -Force -ErrorAction SilentlyContinue
}

Write-Host "Previous servers stopped (if any were running)" -ForegroundColor Green
Write-Host ""

# Check if venv exists
if (-not (Test-Path $venvActivate)) {
    Write-Host "⚠️  Virtual environment not found!" -ForegroundColor Yellow
    Write-Host "Please run: .\setup-backend.bat first" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# Start Backend
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
# Use Base64 encoding to avoid all escaping issues
$backendCmd = @"
Set-Location -LiteralPath '$backendDir'
& '$venvActivate'
python run_server_auto.py
"@
$backendBytes = [System.Text.Encoding]::Unicode.GetBytes($backendCmd)
$backendEncoded = [Convert]::ToBase64String($backendBytes)
Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $backendEncoded -WindowStyle Normal

# Wait a bit
Write-Host "Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
# Use Base64 encoding to avoid all escaping issues
$frontendCmd = @"
Set-Location -LiteralPath '$projectRoot'
npm run dev
"@
$frontendBytes = [System.Text.Encoding]::Unicode.GetBytes($frontendCmd)
$frontendEncoded = [Convert]::ToBase64String($frontendBytes)
Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $frontendEncoded -WindowStyle Normal

# Done
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✅ Servers Starting!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: Check the Frontend window for actual port" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the opened windows for actual URLs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to close this window (servers keep running)..." -ForegroundColor Gray
pause

