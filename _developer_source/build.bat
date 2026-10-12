@echo off
title Building Silver Premium Invoice Generator (.EXE)
echo ========================================================
echo   SILVER PREMIUM TAX INVOICE GENERATOR - EXE BUILDER
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    pause
    exit /b 1
)

echo Installing / Verifying requirements...
python -m pip install -r requirements.txt

echo.
echo Running Build Script...
python build.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   BUILD COMPLETED SUCCESSFULLY!
    echo   Output: dist\SilverPremiumInvoice.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build encountered issues.
)

pause
