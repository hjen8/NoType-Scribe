@echo off
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

:run
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 500" >nul 2>&1

set "BASE_DIR=%~dp0"
set "SKILL_DIR=%BASE_DIR%skills\typeless-scribe"

set "PYTHON_EXE="
if exist "%SKILL_DIR%\venv\Scripts\pythonw.exe" set "PYTHON_EXE=%SKILL_DIR%\venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%BASE_DIR%venv\Scripts\pythonw.exe" set "PYTHON_EXE=%BASE_DIR%venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%BASE_DIR%.venv\Scripts\pythonw.exe" set "PYTHON_EXE=%BASE_DIR%.venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE (
    where pythonw >nul 2>&1 && set "PYTHON_EXE=pythonw.exe"
)
if not defined PYTHON_EXE (
    where python >nul 2>&1 && set "PYTHON_EXE=python.exe"
)

if not defined PYTHON_EXE (
    echo [ERROR] Python not found! Please run setup_new_pc.bat.
    pause
    exit /b 1
)

start "" /d "%SKILL_DIR%" "%PYTHON_EXE%" "main.py"
