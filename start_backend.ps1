# ============================================
# Backend Startup Script
# ============================================

$PORT = 8000
$scriptDir = $PSScriptRoot
$backendDir = Join-Path $scriptDir "backend"
$venvPython = Join-Path $backendDir "venv\Scripts\python.exe"

# Kill existing process
Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

Set-Location $backendDir

if (Test-Path $venvPython) {
    Write-Host "Using virtual environment: $venvPython" -ForegroundColor Gray
    & $venvPython main.py
} else {
    python main.py
}
