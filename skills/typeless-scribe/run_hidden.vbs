Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "e:\AI_Work\NoType\skills\typeless-scribe"
WshShell.Run """e:\AI_Work\NoType\skills\typeless-scribe\venv\Scripts\pythonw.exe"" ""e:\AI_Work\NoType\skills\typeless-scribe\main.py""", 0, False
