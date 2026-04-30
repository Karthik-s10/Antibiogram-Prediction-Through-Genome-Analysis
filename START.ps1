# ============================================
# MASTER STARTUP SCRIPT
# ============================================

$scriptDir = $PSScriptRoot

Write-Host "Launching Antibiogram Prediction System..." -ForegroundColor Green

# Start Backend in a new window
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $scriptDir "start_backend.ps1")

# Start Frontend in a new window
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $scriptDir "start_frontend.ps1")

Write-Host "`nServers are starting in separate windows." -ForegroundColor Yellow
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"
