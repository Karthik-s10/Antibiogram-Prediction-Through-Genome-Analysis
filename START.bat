@echo off
echo ============================================================
echo   Starting Application
echo ============================================================
echo.

REM Get the directory where this batch file is
cd /d "%~dp0"

REM Stop any existing processes first
echo Stopping any existing servers...

REM Stop Node/Vite processes (Frontend)
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *Vite*" 2>nul
taskkill /F /IM node.exe /FI "MEMUSAGE gt 1" 2>nul

REM Stop Python/uvicorn processes (Backend)  
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *Backend*" 2>nul

REM Kill by port if needed
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

echo Previous servers stopped (if any were running)
echo.

REM Check if venv exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: setup-backend.bat first
    echo.
    pause
    exit /b 1
)

REM Start Backend
echo Starting Backend Server...
start "Backend Server" cmd /k "cd /d "%~dp0backend" & .\venv\Scripts\activate & python run_server_auto.py"

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start Frontend
echo Starting Frontend Server...
start "Frontend Server" cmd /k "cd /d "%~dp0" & npm run dev"

echo.
echo ============================================================
echo   Servers Starting!
echo ============================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Check the opened windows for actual URLs
echo.
pause

