@echo off
title JARVIS Voice Assistant Daemon
cd /d "c:\jarvis ai agent desktop"
echo Launching JARVIS Continuous Voice Listener (Wake word: 'Jarvis')...
python -m jarvis.main --mode voice
if errorlevel 1 pause
