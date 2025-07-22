@echo off
echo ==========================================
echo Installing Node Dependencies for SCRAPE
echo ==========================================
pushd "%~dp0..\scrape"
echo Running npm install in %CD%
npm install
popd
echo.
echo Done!
pause 