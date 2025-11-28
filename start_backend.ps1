# ============================================
# Backend Startup Script
# Antibiogram Prediction System
# ============================================

$PORT = 8000
$ServerHost = "localhost"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BACKEND SERVER STARTUP" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing process on the port
Write-Host "[1/4] Checking for existing processes on port $PORT..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcess) {
    foreach ($procId in $existingProcess) {
        Write-Host "      Killing process $procId on port $PORT..." -ForegroundColor Red
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "      Previous process terminated." -ForegroundColor Green
} else {
    Write-Host "      Port $PORT is free." -ForegroundColor Green
}

# Check/create virtual environment
Write-Host "[2/4] Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "backend\venv\Scripts\python.exe")) {
    Write-Host "      Creating virtual environment..." -ForegroundColor Yellow
    python -m venv backend\venv
    Write-Host "      Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "      Virtual environment exists." -ForegroundColor Green
}

# Install/update dependencies
Write-Host "[3/4] Checking dependencies..." -ForegroundColor Yellow
$pipCheck = & backend\venv\Scripts\pip.exe show fastapi 2>$null
if (-not $pipCheck) {
    Write-Host "      Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    & backend\venv\Scripts\pip.exe install -r backend\requirements.txt --quiet
    Write-Host "      Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "      Dependencies already installed." -ForegroundColor Green
}

# Start the server
Write-Host "[4/4] Starting FastAPI server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Backend running on http://localhost:$PORT" -ForegroundColor Green
Write-Host "  API Docs: http://localhost:$PORT/docs" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Set-Location backend
& .\venv\Scripts\python.exe -m uvicorn main:app --reload --host $ServerHost --port $PORT
