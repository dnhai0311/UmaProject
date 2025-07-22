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
echo 2. Scrape Data
echo 3. Install Dependencies
echo 4. Delete Data
echo 5. Exit
echo.
echo ========================================
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto start_scanner
if "%choice%"=="2" goto scrape_data
if "%choice%"=="3" goto install_deps
if "%choice%"=="4" goto delete_data
if "%choice%"=="5" goto exit
goto menu

:start_scanner
cls
echo Starting Event Scanner...
call run\start_scanner.bat
goto menu

:install_deps
cls
echo Installing Python dependencies...
call run\install_dependencies.bat
echo.
echo Installing NPM dependencies in /scrape...
call run\install_scrape_dependencies.bat
goto menu

:scrape_data
cls
echo Running Data Scraper...
call run\scrape_data.bat
goto menu

:delete_data
cls
echo Launching Delete Data Tool...
call run\delete_data.bat
goto menu

:exit
echo Goodbye!
pause
exit 