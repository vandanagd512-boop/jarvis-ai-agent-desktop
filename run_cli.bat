@echo off
title JARVIS AI Desktop Assistant
cd /d "c:\jarvis ai agent desktop"
echo Launching JARVIS Interactive Assistant...
python -m jarvis.main --mode cli
if errorlevel 1 pause
