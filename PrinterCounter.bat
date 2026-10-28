@echo off
setlocal
cd /d "%~dp0"
title Printer Counter Portable

:: Check if pythonw (windowless) is available
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw "%~dp0printer_counter.py" %*
    exit /b 0
)

:: Check if python is available
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" python "%~dp0printer_counter.py" %*
    exit /b 0
)

:: Check py launcher
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" py "%~dp0printer_counter.py" %*
    exit /b 0
)

echo [ERROR] Python was not found in your system PATH.
echo Please ensure Python is installed or run with an embedded Python folder.
pause

