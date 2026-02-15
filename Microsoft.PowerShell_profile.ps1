# PowerShell profile for Antibiogram project
# Automatically activates virtual environment when opening PowerShell in this directory

# Check if we're in the project directory
if (Test-Path ".\activate-venv.ps1") {
    .\activate-venv.ps1
}
