# Auto-activate virtual environment for Antibiogram project
if (Test-Path "e:\Antibiogram-Prediction-Through-Genome-Analysis\backend\venv\Scripts\Activate.ps1") {
    & "e:\Antibiogram-Prediction-Through-Genome-Analysis\backend\venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Creating new one..."
    cd "e:\Antibiogram-Prediction-Through-Genome-Analysis\backend"
    python -m venv venv
    & "e:\Antibiogram-Prediction-Through-Genome-Analysis\backend\venv\Scripts\Activate.ps1"
}
