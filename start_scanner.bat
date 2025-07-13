@echo off
echo Starting Uma Event Scanner...
echo.

cd /d "%~dp0"
cd event_scanner
py event_scanner.py

echo.
echo Scanner closed.
pause 