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
start "" "%~dp0skills\typeless-scribe\venv\Scripts\pythonw.exe" "%~dp0skills\typeless-scribe\main.py"

