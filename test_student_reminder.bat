@echo off
chcp 65001 >nul
echo 正在開啟 NoType 7 月學生名單例行檢核測試視窗...
"%~dp0skills\typeless-scribe\venv\Scripts\python.exe" -c "import sys; sys.path.append(r'%~dp0skills\typeless-scribe'); from ui_manager import ui; ui.show_student_reminder_dialog(force=True); ui.root.mainloop()"
