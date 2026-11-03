@echo off
title J.A.R.V.I.S. Interactive CMD Engine
cd /d "c:\jarvis ai agent desktop"
cls
echo ======================================================================
echo           J. A. R. V. I. S.   C O M M A N D   P R O M P T
echo ======================================================================
echo   Directory: c:\jarvis ai agent desktop
echo   Background Voice: ONLINE (Microphone continuously listening)
echo.
echo   You can speak into your mic OR type in this window:
echo     - open whatsapp / open instagram / open youtube
echo     - text someone hello / call someone
echo     - search song faded / play believer
echo     - take a screenshot / where am I / lock my pc
echo ======================================================================
echo.
python -m jarvis.main --mode cli
pause
