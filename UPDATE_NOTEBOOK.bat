@echo off
title NoType - Quick Update
echo ===================================================
echo   NoType - Quick Update from Dropbox
echo ===================================================
echo.
echo Stopping running NoType process...
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 1 >nul

if exist "E:\AI_Work\NoType" (
    set "TARGET_DIR=E:\AI_Work\NoType"
) else (
    set "TARGET_DIR=C:\AI_Work\NoType"
)

echo Updating files in %TARGET_DIR%...
set "DROPBOX_SRC=%~dp0"
set "SKILL_DIR=%TARGET_DIR%\skills\typeless-scribe"

if exist "%DROPBOX_SRC%keyboard_hook.py" copy /y "%DROPBOX_SRC%keyboard_hook.py" "%SKILL_DIR%\keyboard_hook.py" >nul
if exist "%DROPBOX_SRC%ui_manager.py" copy /y "%DROPBOX_SRC%ui_manager.py" "%SKILL_DIR%\ui_manager.py" >nul
if exist "%DROPBOX_SRC%history_manager.py" copy /y "%DROPBOX_SRC%history_manager.py" "%SKILL_DIR%\history_manager.py" >nul
if exist "%DROPBOX_SRC%audio_logic.py" copy /y "%DROPBOX_SRC%audio_logic.py" "%SKILL_DIR%\audio_logic.py" >nul
if exist "%DROPBOX_SRC%dictionary.txt" copy /y "%DROPBOX_SRC%dictionary.txt" "%SKILL_DIR%\dictionary.txt" >nul
if exist "%DROPBOX_SRC%corrections.json" copy /y "%DROPBOX_SRC%corrections.json" "%SKILL_DIR%\corrections.json" >nul
if exist "%DROPBOX_SRC%config.json" copy /y "%DROPBOX_SRC%config.json" "%SKILL_DIR%\config.json" >nul
if exist "%DROPBOX_SRC%setup_new_pc.bat" copy /y "%DROPBOX_SRC%setup_new_pc.bat" "%TARGET_DIR%\setup_new_pc.bat" >nul
if exist "%DROPBOX_SRC%start_admin.bat" copy /y "%DROPBOX_SRC%start_admin.bat" "%TARGET_DIR%\start_admin.bat" >nul

echo [OK] Files updated successfully!
echo Starting NoType in background...
cd /d "%TARGET_DIR%"
call "%TARGET_DIR%\start_admin.bat"

echo.
echo ===================================================
echo   [SUCCESS] NoType updated and running!
echo   You can now press ~ (tilde key) to voice input!
echo ===================================================
timeout /t 3 >nul
