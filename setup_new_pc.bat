@echo off
setlocal enabledelayedexpansion
title NoType - PC Setup and Recovery Tool

echo ===================================================
echo   NoType Scribe - New PC Setup and Recovery Tool
echo ===================================================
echo.

:: 1. Check Python installation
echo [1/5] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found on PATH!
    echo.
    echo Please install Python 3.10+ from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Make sure to CHECK "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] Found %%v

:: 2. Set up virtual environment
set "VENV_DIR=%~dp0skills\typeless-scribe\venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

echo.
echo [2/5] Checking virtual environment...
if not exist "%PYTHON_EXE%" (
    echo [INFO] Creating new virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Existing virtual environment found.
)

:: 3. Install/update dependencies
echo.
echo [3/5] Installing dependencies from requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1
"%PIP_EXE%" install -r "%~dp0skills\typeless-scribe\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install some dependencies.
    pause
    exit /b 1
)
echo [OK] All dependencies installed successfully.

:: 4. Restore configuration and dictionary from Dropbox backup if available
echo.
echo [4/5] Checking cloud backup and restoring configuration...
"%PYTHON_EXE%" -c "import sys; sys.path.append(r'%~dp0skills\typeless-scribe'); from backup_manager import restore_from_backup, sync_to_backup; restore_from_backup(); sync_to_backup()"
if exist "%~dp0skills\typeless-scribe\config.json" (
    echo [OK] Configuration and dictionary ready.
) else (
    echo [NOTICE] No config.json found in backup. Creating default template...
    echo {"GROQ_API_KEY": ""} > "%~dp0skills\typeless-scribe\config.json"
    echo [IMPORTANT] Please open skills\typeless-scribe\config.json and set your GROQ_API_KEY.
)

:: 5. Create Desktop shortcut
echo.
echo [5/5] Creating Desktop Shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\NoType 語音輸入.lnk"
set "TARGET_BAT=%~dp0start_admin.bat"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'NoType Scribe Audio Input'; $s.Save()" >nul 2>&1
if exist "%SHORTCUT_PATH%" (
    echo [OK] Desktop shortcut created: "NoType 語音輸入"
) else (
    echo [INFO] Could not create shortcut automatically, you can run start_admin.bat directly.
)

echo.
echo ===================================================
echo   [SUCCESS] NoType setup is complete!
echo ===================================================
echo.
set /p LAUNCH="Do you want to start NoType now? (Y/N, default Y): "
if /i "%LAUNCH%"=="N" (
    echo You can start NoType anytime by clicking "NoType 語音輸入" on your Desktop.
) else (
    echo Starting NoType in background...
    call "%TARGET_BAT%"
    echo [OK] NoType is now running! Look for the blue icon in the system tray.
)

timeout /t 3 >nul
