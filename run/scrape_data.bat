@echo off
title Uma Project - Data Scraper
color 0B

:menu
cls
echo ==========================================
echo        UMA PROJECT ^- DATA SCRAPER
echo ==========================================
echo.
echo 1. Scrape Skills
echo 2. Scrape Uma Characters
echo 3. Scrape Support Cards
echo 4. Scrape Events
echo 5. Scrape ALL (Skills ^> Uma ^> Support ^> Events)
echo 6. Back
echo.
echo ==========================================
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto skills
if "%choice%"=="2" goto uma
if "%choice%"=="3" goto support
if "%choice%"=="4" goto events
if "%choice%"=="5" goto all
if "%choice%"=="6" exit /b
goto menu

rem ----------------------
rem Helper subroutines (no pause)
rem ----------------------
:skills_run
echo Running Skill Scraper...
node scrape\skill-scrape.js
goto :eof

:uma_run
echo Running Uma Character Scraper...
node scrape\uma-scrape.js
goto :eof

:support_run
echo Running Support Card Scraper...
node scrape\support-scrape.js
goto :eof

:events_run
echo Running Event Scraper...
node scrape\event-scrape.js
goto :eof

rem ----------------------
rem Interactive labels (with pause)
rem ----------------------
:skills
call :skills_run
pause
goto menu

:uma
call :uma_run
pause
goto menu

:support
call :support_run
pause
goto menu

:events
call :events_run
pause
goto menu


:all
call :skills_run
call :uma_run
call :support_run
call :events_run
echo.
echo All scraping tasks completed.
echo.
goto menu 