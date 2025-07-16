@echo off
title Uma Project Launcher
color 0A

:menu
cls
echo ========================================
echo           UMA PROJECT LAUNCHER
echo ========================================
echo.
echo Choose an option:
echo.
echo 1. Start Event Scanner
echo 2. Start Web Interface
echo 3. Install Dependencies
echo 4. Exit
echo.
echo ========================================
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto start_scanner
if "%choice%"=="2" goto start_web
if "%choice%"=="3" goto install_deps
if "%choice%"=="4" goto exit
goto menu

:start_scanner
cls
echo Starting Event Scanner...
call run\start_scanner.bat
goto menu

:start_web
cls
echo Starting Web Interface...
call run\start_web.bat
goto menu

:install_deps
cls
echo Installing Dependencies...
call run\install_dependencies.bat
goto menu

:exit
echo Goodbye!
pause
exit 