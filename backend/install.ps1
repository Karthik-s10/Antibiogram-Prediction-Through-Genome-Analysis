# Change to script directory
Set-Location $PSScriptRoot

Write-Host "Installing Python packages..." -ForegroundColor Cyan
pip install -r requirements.txt
Write-Host ""
Write-Host "Checking Visual C++ Redistributables..." -ForegroundColor Cyan
python -c "import install_vc_redist; install_vc_redist.main()"
Write-Host ""
Write-Host "Installation complete! Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

