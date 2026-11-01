@echo off
title SONORA Studio
cd /d "%~dp0"

:: 1. Try pythonw in PATH or virtualenv
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw main.py
    exit
)

:: 2. Try standard Python 3.15 / 3.12 / 3.11 default paths
if exist "C:\Program Files\Python315\pythonw.exe" (
    start "" "C:\Program Files\Python315\pythonw.exe" main.py
    exit
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" main.py
    exit
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" main.py
    exit
)

:: 3. Fallback to standard python in PATH
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" python main.py
    exit
)

echo [HATA] Python bulunamadi. Lutfen Python'in yuklu ve PATH'e ekli oldugundan emin olun.
pause
