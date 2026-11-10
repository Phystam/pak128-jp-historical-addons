@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ========================================================
echo  Simutrans Addon Build Pipeline (datt + spreadsheet)
echo ========================================================
ruby scripts/make.rb all
echo.
pause
