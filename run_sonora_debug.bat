@echo off
title SONORA Studio - Gelistirici / Hata Ayiklama Modu
echo ========================================================
echo   SONORA STUDIO - KONSOL LOGLARI VE HATA AYIKLAMA
echo ========================================================
echo.
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Uygulama calisirken bir hata olustu.
    pause
)
