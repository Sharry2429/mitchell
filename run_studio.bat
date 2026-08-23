@echo off
REM Launch Mitchell Studio Web Command Center from ANY directory
setlocal
set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%
cd /d "%SCRIPT_DIR%"

echo ========================================================
echo   Launching Mitchell AI Command-Driven Studio Center
echo   URL: http://localhost:8500
echo ========================================================
start "" http://localhost:8500
python -m mitchell.cli studio
endlocal
