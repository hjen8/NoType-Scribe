@echo off
setlocal enabledelayedexpansion
title NoType - Quick Update
echo ===================================================
echo   NoType - Quick Update from Dropbox
echo ===================================================
echo.
echo Stopping running NoType process...
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
timeout /t 1 >nul

set "TARGET_DIR="
if exist "C:\AI_Work\NoType\skills\typeless-scribe\main.py" (
    set "TARGET_DIR=C:\AI_Work\NoType"
) else if exist "E:\AI_Work\NoType\skills\typeless-scribe\main.py" (
    set "TARGET_DIR=E:\AI_Work\NoType"
) else if exist "C:\AI_Work\NoType" (
    set "TARGET_DIR=C:\AI_Work\NoType"
) else if exist "E:\AI_Work\NoType" (
    set "TARGET_DIR=E:\AI_Work\NoType"
)

if not defined TARGET_DIR (
    echo.
    echo [INFO] Standard NoType directory not detected.
    echo Default: C:\AI_Work\NoType
    set /p USER_DIR="Enter your NoType folder path (or press Enter for C:\AI_Work\NoType): "
    if "!USER_DIR!"=="" (
        set "TARGET_DIR=C:\AI_Work\NoType"
    ) else (
        set "TARGET_DIR=!USER_DIR!"
    )
)

echo Updating files in %TARGET_DIR%...
set "DROPBOX_SRC=%~dp0"
set "SKILL_DIR=%TARGET_DIR%\skills\typeless-scribe"

if not exist "%SKILL_DIR%" mkdir "%SKILL_DIR%"

REM 儲存 Dropbox 來源路徑供筆電端自動鏡像診斷日誌使用
echo %DROPBOX_SRC% > "%SKILL_DIR%\dropbox_path.txt"

copy /y "%DROPBOX_SRC%*.py" "%SKILL_DIR%\" >nul
copy /y "%DROPBOX_SRC%*.json" "%SKILL_DIR%\" >nul
copy /y "%DROPBOX_SRC%*.txt" "%SKILL_DIR%\" >nul
copy /y "%DROPBOX_SRC%*.bat" "%TARGET_DIR%\" >nul

echo [OK] All Python scripts, configs, and dictionaries updated successfully!
echo Starting NoType in background...
cd /d "%TARGET_DIR%"
call "%TARGET_DIR%\start_admin.bat"

echo.
echo ===================================================
echo   [SUCCESS] NoType updated and running!
echo   You can now press ~ (tilde key) to voice input!
echo ===================================================
timeout /t 3 >nul
