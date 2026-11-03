@echo off
title JARVIS Test Verification Suite
cd /d "c:\jarvis ai agent desktop"
echo Running complete verification test suite...
python -u tests/run_tests.py
pause
