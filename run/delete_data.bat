@echo off
title UMA Project - Delete Data
color 0C
:menu
cls
echo =====================================
echo        DELETE DATA FILES
echo =====================================
echo 1. Delete skills.json
echo 2. Delete uma_char.json
echo 3. Delete support_card.json
echo 4. Delete events.json
echo 5. Delete ALL data files
echo 6. Back
set /p dchoice="Select option (1-6): "
set datapath=%~dp0..\data
if "%dchoice%"=="1" del "%datapath%\skills.json"
if "%dchoice%"=="2" del "%datapath%\uma_char.json"
if "%dchoice%"=="3" del "%datapath%\support_card.json"
if "%dchoice%"=="4" del "%datapath%\events.json"
if "%dchoice%"=="5" del /q "%datapath%\skills.json" "%datapath%\uma_char.json" "%datapath%\support_card.json" "%datapath%\events.json"
if "%dchoice%"=="6" exit /b
pause
goto menu 