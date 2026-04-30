#!/bin/bash

# ============================================
# Antibiogram Prediction System - Bash Entry
# ============================================

# Convert current directory to Windows format for PowerShell
WIN_DIR=$(pwd -W)

echo "Starting system via PowerShell orchestrator..."

# Launch the Master PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "$WIN_DIR/START.ps1"

echo "Done. Check the new windows for server logs."
