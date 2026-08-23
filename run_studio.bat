@echo off
REM Launch Mitchell Studio Web Command Center
echo ========================================================
echo   Launching Mitchell AI Command-Driven Studio Center
echo   URL: http://localhost:8500
echo ========================================================
start "" http://localhost:8500
python -m mitchell.cli studio
