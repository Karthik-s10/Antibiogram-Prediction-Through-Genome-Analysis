@echo off
cd /d "%~dp0"
echo Installing Python packages...
pip install -r requirements.txt
echo.
echo Checking Visual C++ Redistributables...
python -c "import install_vc_redist; install_vc_redist.main()"
pause

