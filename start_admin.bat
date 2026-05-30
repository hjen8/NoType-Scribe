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
start "" "e:\AI_Work\NoType\skills\typeless-scribe\venv\Scripts\pythonw.exe" "e:\AI_Work\NoType\skills\typeless-scribe\main.py"
