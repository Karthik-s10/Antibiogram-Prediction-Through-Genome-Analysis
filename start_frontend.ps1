# ============================================
# Frontend Startup Script
# Antibiogram Prediction System
# ============================================

$PORT = 5173

Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  FRONTEND SERVER STARTUP" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# Kill any existing process on the port
Write-Host "[1/3] Checking for existing processes on port $PORT..." -ForegroundColor Yellow
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

# Check/install node modules
Write-Host "[2/3] Checking node modules..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "      Installing npm dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    npm install --silent
    Write-Host "      Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "      Node modules exist." -ForegroundColor Green
}

# Start the dev server
Write-Host "[3/3] Starting Vite dev server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Frontend running on http://localhost:$PORT" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Use npx to run Vite directly and avoid npm CLI warnings
npx vite --port $PORT --host localhost
