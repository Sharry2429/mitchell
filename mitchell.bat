@echo off
REM Mitchell CLI Universal Windows Entry Point
setlocal
set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%
python -m mitchell.cli %*
endlocal
