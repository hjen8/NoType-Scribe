@echo off
setlocal enabledelayedexpansion
title NoType - One-Click Installer from Dropbox

echo =========================================================
echo   NoType Scribe - One-Click Installer from Dropbox
echo =========================================================
echo.
echo This script will install NoType on this computer and restore
echo your API keys, custom dictionary (342+ words), and settings.
echo.

:: 1. Check Python
echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not found on PATH!
    echo.
    echo Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Make sure to CHECK "Add Python to PATH" during installation!
    echo After installing Python, run this batch file again.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] Found %%v

:: 2. Choose target installation directory
echo.
echo [2/4] Setting target installation path...
if exist "E:\" (
    set "DEFAULT_DIR=E:\AI_Work\NoType"
) else (
    set "DEFAULT_DIR=C:\AI_Work\NoType"
)

echo Default installation path: %DEFAULT_DIR%
set /p TARGET_DIR="Press Enter to use default or type target directory: "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_DIR%"

echo [INFO] Installing to: %TARGET_DIR%
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1

:: 3. Download or sync NoType codebase from GitHub
echo.
echo [3/4] Fetching latest NoType codebase...
if exist "%TARGET_DIR%\skills\typeless-scribe\main.py" (
    echo [OK] Existing codebase found in %TARGET_DIR%.
) else (
    where git >nul 2>&1
    if !errorlevel! == 0 (
        echo [INFO] Git found. Cloning from GitHub repository...
        git clone https://github.com/hjen8/NoType-Scribe.git "%TARGET_DIR%"
    ) else (
        echo [INFO] Git not found. Downloading release package via PowerShell...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$zip='%temp%\notype_dl.zip'; $dest='%temp%\notype_extracted'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/hjen8/NoType-Scribe/archive/refs/heads/main.zip' -OutFile $zip; Expand-Archive -Path $zip -DestinationPath $dest -Force; Copy-Item -Path \"$dest\NoType-Scribe-main\*\" -Destination '%TARGET_DIR%' -Recurse -Force; Remove-Item $zip -Force; Remove-Item $dest -Recurse -Force"
    )
)

if not exist "%TARGET_DIR%\skills\typeless-scribe\main.py" (
    echo [ERROR] Failed to obtain NoType codebase. Please check your internet connection.
    pause
    exit /b 1
)
echo [OK] Codebase is ready.

:: 4. Restore configuration & dictionary directly from this Dropbox folder
echo.
echo [4/4] Restoring your config.json, dictionary.txt, corrections.json from Dropbox...
set "DROPBOX_SRC=%~dp0"
set "SKILL_DIR=%TARGET_DIR%\skills\typeless-scribe"

if exist "%DROPBOX_SRC%config.json" (
    copy /y "%DROPBOX_SRC%config.json" "%SKILL_DIR%\config.json" >nul
    echo [OK] Restored config.json (API Key)
)
if exist "%DROPBOX_SRC%dictionary.txt" (
    copy /y "%DROPBOX_SRC%dictionary.txt" "%SKILL_DIR%\dictionary.txt" >nul
    echo [OK] Restored dictionary.txt (342+ specialized words)
)
if exist "%DROPBOX_SRC%corrections.json" (
    copy /y "%DROPBOX_SRC%corrections.json" "%SKILL_DIR%\corrections.json" >nul
    echo [OK] Restored corrections.json (active learning pairs)
)

:: 5. Run setup_new_pc.bat to finish environment setup
echo.
echo =========================================================
echo   Code and settings deployed! Running environment setup...
echo =========================================================
echo.
cd /d "%TARGET_DIR%"
call "%TARGET_DIR%\setup_new_pc.bat"

exit /b 0
