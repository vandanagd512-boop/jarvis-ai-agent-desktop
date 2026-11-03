@echo off
title J.A.R.V.I.S. Production Web Dashboard
cd /d "c:\jarvis ai agent desktop"
cls
echo ======================================================================
echo           J. A. R. V. I. S.   A I   A G E N T   D E S K T O P
echo ======================================================================
echo   Directory: c:\jarvis ai agent desktop
echo   Mode: Web Production Dashboard + Voice Engine
echo   Address: http://127.0.0.1:8765
echo ======================================================================
echo.
echo Checking for previous instances on port 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765') do taskkill /f /pid %%a >nul 2>&1
echo Starting JARVIS server...
python -m jarvis.main --mode web
pause
