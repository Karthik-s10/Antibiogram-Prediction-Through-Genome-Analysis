# ============================================
# MASTER STARTUP SCRIPT
# Antibiogram Prediction System
# ============================================
# Launches both Backend and Frontend servers
# in separate PowerShell windows
# ============================================

Write-Host ""
Write-Host "============================================" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "  ANTIBIOGRAM PREDICTION SYSTEM" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "  Starting all services..." -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "============================================" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start Backend in a new window
Write-Host "[1/2] Launching Backend Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", "$scriptDir\start_backend.ps1" -WorkingDirectory $scriptDir

Start-Sleep -Seconds 3

# Start Frontend in a new window
Write-Host "[2/2] Launching Frontend Server..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-File", "$scriptDir\start_frontend.ps1" -WorkingDirectory $scriptDir

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SERVICES LAUNCHED!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Close this window or the spawned windows" -ForegroundColor Yellow
Write-Host "  to stop the servers." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Green

# Keep this window open briefly so user can see the summary
Start-Sleep -Seconds 5
