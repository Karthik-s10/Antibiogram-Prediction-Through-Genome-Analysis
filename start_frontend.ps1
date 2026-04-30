# ============================================
# Frontend Startup Script
# ============================================

$PORT = 5173
$scriptDir = $PSScriptRoot

# Kill existing process
Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

Set-Location $scriptDir
npm run dev
