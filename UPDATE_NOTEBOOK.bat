@echo off
setlocal enabledelayedexpansion
title NoType - Quick Update
echo ===================================================
echo   NoType - Quick Update
echo ===================================================
echo.
echo [1/4] Stopping running NoType processes...
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
timeout /t 1 >nul

echo [2/4] Detecting NoType installation directory...
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
    echo [INFO] Standard NoType directory not found.
    set /p USER_DIR="Enter NoType path (or press Enter for C:\AI_Work\NoType): "
    if "!USER_DIR!"=="" (
        set "TARGET_DIR=C:\AI_Work\NoType"
    ) else (
        set "TARGET_DIR=!USER_DIR!"
    )
)

echo [INFO] Target directory: %TARGET_DIR%
set "SKILL_DIR=%TARGET_DIR%\skills\typeless-scribe"
if not exist "%SKILL_DIR%" mkdir "%SKILL_DIR%" >nul 2>&1

REM Detect actual Dropbox source directory
set "DROPBOX_SRC="
if exist "%~dp0run_hidden.vbs" (
    set "DROPBOX_SRC=%~dp0"
) else if exist "%USERPROFILE%\Dropbox\Brain\NoType_Backup\run_hidden.vbs" (
    set "DROPBOX_SRC=%USERPROFILE%\Dropbox\Brain\NoType_Backup\"
) else if exist "D:\Dropbox\Brain\NoType_Backup\run_hidden.vbs" (
    set "DROPBOX_SRC=D:\Dropbox\Brain\NoType_Backup\"
) else if exist "C:\Dropbox\Brain\NoType_Backup\run_hidden.vbs" (
    set "DROPBOX_SRC=C:\Dropbox\Brain\NoType_Backup\"
) else (
    set "DROPBOX_SRC=%~dp0"
)

echo [INFO] Source directory: !DROPBOX_SRC!
echo !DROPBOX_SRC!> "%SKILL_DIR%\dropbox_path.txt"

echo [3/4] Copying latest files...
if exist "!DROPBOX_SRC!run_hidden.vbs" (
    copy /y "!DROPBOX_SRC!*.py" "%SKILL_DIR%\" >nul
    copy /y "!DROPBOX_SRC!*.json" "%SKILL_DIR%\" >nul
    copy /y "!DROPBOX_SRC!*.txt" "%SKILL_DIR%\" >nul
    copy /y "!DROPBOX_SRC!*.bat" "%TARGET_DIR%\" >nul
    copy /y "!DROPBOX_SRC!*.vbs" "%SKILL_DIR%\" >nul
    copy /y "!DROPBOX_SRC!*.vbs" "%TARGET_DIR%\" >nul
    echo [OK] Files copied from Dropbox!
) else (
    echo [INFO] Dropbox backup not found locally, pulling latest files from GitHub...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/hjen8/NoType-Scribe/main/skills/typeless-scribe/run_hidden.vbs' -OutFile '%SKILL_DIR%\run_hidden.vbs' -UseBasicParsing" >nul 2>&1
    echo [OK] run_hidden.vbs updated from GitHub!
)

REM Guarantee run_hidden.vbs is dynamic and correct
(
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo Set WinScriptHost = CreateObject^("WScript.Shell"^)
echo strScriptDir = fso.GetParentFolderName^(WScript.ScriptFullName^)
echo strSkillsDir = fso.GetParentFolderName^(strScriptDir^)
echo strNoTypeDir = fso.GetParentFolderName^(strSkillsDir^)
echo strBatPath = strNoTypeDir ^& "\start_admin.bat"
echo If Not fso.FileExists^(strBatPath^) Then
echo     If fso.FileExists^(strScriptDir ^& "\start_admin.bat"^) Then
echo         strBatPath = strScriptDir ^& "\start_admin.bat"
echo     ElseIf fso.FileExists^("C:\AI_Work\NoType\start_admin.bat"^) Then
echo         strBatPath = "C:\AI_Work\NoType\start_admin.bat"
echo     ElseIf fso.FileExists^("E:\AI_Work\NoType\start_admin.bat"^) Then
echo         strBatPath = "E:\AI_Work\NoType\start_admin.bat"
echo     End If
echo End If
echo If fso.FileExists^(strBatPath^) Then
echo     WinScriptHost.Run Chr^(34^) ^& strBatPath ^& Chr^(34^), 0
echo End If
echo Set WinScriptHost = Nothing
echo Set fso = Nothing
) > "%SKILL_DIR%\run_hidden.vbs"

echo [OK] run_hidden.vbs verified!
echo.
echo [INFO] Configuring Boot Auto-Start...
schtasks /create /tn "NoType_AutoStart" /tr "wscript.exe \"%SKILL_DIR%\run_hidden.vbs\"" /sc onlogon /rl highest /f >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\NoType Scribe.lnk'); $s.TargetPath = '%TARGET_DIR%\start_admin.bat'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.Description = 'NoType Scribe Auto-Start'; $s.Save()" >nul 2>&1

echo.
echo [4/4] Starting NoType in background...
cd /d "%TARGET_DIR%"
call "%TARGET_DIR%\start_admin.bat"

echo.
echo ===================================================
echo   [SUCCESS] NoType updated and launched!
echo   You can now press ~ (tilde key) to dictate!
echo ===================================================
timeout /t 3 >nul
