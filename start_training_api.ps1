# PowerShell script to start the training API server

Write-Host "Starting Antibiogram Prediction Training API..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "backend\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "backend\venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv backend\venv
    & "backend\venv\Scripts\Activate.ps1"
    
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r backend\requirements.txt
}

# Navigate to backend directory
Set-Location backend

# Start the FastAPI server
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host "API Documentation available at http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "" 
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
