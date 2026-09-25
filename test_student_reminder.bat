@echo off
start "" "%~dp0skills\typeless-scribe\venv\Scripts\pythonw.exe" -c "import sys; sys.path.append(r'%~dp0skills\typeless-scribe'); from ui_manager import ui; ui.show_student_reminder_dialog(force=True); ui.root.mainloop()"
exit
