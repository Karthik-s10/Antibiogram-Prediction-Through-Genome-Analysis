@echo off
echo ========================================
echo Fixing Python Package Installation Issues
echo ========================================
echo.
echo This script will:
echo 1. Stop any running Python processes
echo 2. Stop any processes using the venv
echo 3. Allow you to reinstall packages
echo.
pause

echo.
echo Stopping Python processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

echo.
echo Stopping uvicorn processes...
for /f "tokens=2" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo Waiting 2 seconds for processes to close...
timeout /t 2 /nobreak >nul

echo.
echo Now try running:
echo   pip install -r requirements.txt --upgrade
echo.
echo If you still get errors, try:
echo   pip install -r requirements.txt --upgrade --no-cache-dir
echo.
pause

