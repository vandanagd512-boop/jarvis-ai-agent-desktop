@echo off
title JARVIS REST and WebSocket API Server
cd /d "c:\jarvis ai agent desktop"
echo Starting JARVIS API Server on http://127.0.0.1:8765...
python -m jarvis.main --mode api --port 8765
if errorlevel 1 pause
