@echo off
title Silver Premium Invoice Generator - Instant Python Runner
echo Launching Silver Premium Invoice Generator...
cd /d "%~dp0\_developer_source"
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code: %errorlevel%
    pause
)
