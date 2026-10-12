@echo off
title Silver Premium Invoice Generator - Launcher
cd /d "%~dp0"

if exist "Silver Premium Updater.exe" (
    start "" "Silver Premium Updater.exe"
    exit /b 0
)

if exist "Silver Premium Invoice Generator Setup.exe" (
    start "" "Silver Premium Invoice Generator Setup.exe"
    exit /b 0
)

if exist "C:\Users\%USERNAME%\OneDrive\Desktop\Silver Premium Updater.exe" (
    start "" "C:\Users\%USERNAME%\OneDrive\Desktop\Silver Premium Updater.exe"
    exit /b 0
)

if exist "C:\Users\%USERNAME%\OneDrive\Desktop\Silver Premium Invoice Generator Setup.exe" (
    start "" "C:\Users\%USERNAME%\OneDrive\Desktop\Silver Premium Invoice Generator Setup.exe"
    exit /b 0
)

if exist "C:\Users\%USERNAME%\Desktop\Silver Premium Updater.exe" (
    start "" "C:\Users\%USERNAME%\Desktop\Silver Premium Updater.exe"
    exit /b 0
)

if exist "C:\Users\%USERNAME%\Desktop\Silver Premium Invoice Generator Setup.exe" (
    start "" "C:\Users\%USERNAME%\Desktop\Silver Premium Invoice Generator Setup.exe"
    exit /b 0
)

echo [ERROR] Could not locate Silver Premium Updater.exe or Setup.exe.
pause
exit /b 1
