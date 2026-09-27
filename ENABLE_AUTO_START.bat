@echo off
setlocal enabledelayedexpansion
title NoType - Enable Boot Auto-Start

REM Check Administrator Privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator Privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ===================================================
echo   NoType Scribe - Enable Boot Auto-Start
echo ===================================================
echo.

set "TARGET_DIR="
if exist "%~dp0skills\typeless-scribe\run_hidden.vbs" (
    set "TARGET_DIR=%~dp0"
) else if exist "C:\AI_Work\NoType\skills\typeless-scribe\run_hidden.vbs" (
    set "TARGET_DIR=C:\AI_Work\NoType"
) else if exist "E:\AI_Work\NoType\skills\typeless-scribe\run_hidden.vbs" (
    set "TARGET_DIR=E:\AI_Work\NoType"
)

if not defined TARGET_DIR (
    echo [ERROR] NoType directory not found!
    pause
    exit /b 1
)

REM Remove trailing backslash if present
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

set "VBS_PATH=%TARGET_DIR%\skills\typeless-scribe\run_hidden.vbs"
set "BAT_PATH=%TARGET_DIR%\start_admin.bat"

echo [1/2] Registering Windows Scheduled Task (NoType_AutoStart)...
schtasks /create /tn "NoType_AutoStart" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /rl highest /f
if %errorlevel% equ 0 (
    echo [OK] Scheduled Task created with Highest Privileges!
) else (
    echo [WARNING] Failed to create Scheduled Task.
)

echo.
echo [2/2] Creating Startup Folder Dual Backup Shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\NoType Scribe.lnk'); $s.TargetPath = '%BAT_PATH%'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.Description = 'NoType Scribe Auto-Start'; $s.Save()" >nul 2>&1
echo [OK] Dual backup shortcut created in Startup folder.

echo.
echo ===================================================
echo   [SUCCESS] Boot Auto-Start is now ENABLED!
echo   NoType will start automatically when you log in.
echo ===================================================
timeout /t 3 >nul
