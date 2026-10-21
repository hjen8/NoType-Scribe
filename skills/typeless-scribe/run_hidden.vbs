Set fso = CreateObject("Scripting.FileSystemObject")
Set WinScriptHost = CreateObject("WScript.Shell")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strSkillsDir = fso.GetParentFolderName(strScriptDir)
strNoTypeDir = fso.GetParentFolderName(strSkillsDir)

strBatPath = strNoTypeDir & "\start_admin.bat"

If Not fso.FileExists(strBatPath) Then
    If fso.FileExists(strScriptDir & "\start_admin.bat") Then
        strBatPath = strScriptDir & "\start_admin.bat"
    ElseIf fso.FileExists("C:\AI_Work\NoType\start_admin.bat") Then
        strBatPath = "C:\AI_Work\NoType\start_admin.bat"
    ElseIf fso.FileExists("E:\AI_Work\NoType\start_admin.bat") Then
        strBatPath = "E:\AI_Work\NoType\start_admin.bat"
    End If
End If

If fso.FileExists(strBatPath) Then
    WinScriptHost.Run Chr(34) & strBatPath & Chr(34), 0
End If

Set WinScriptHost = Nothing
Set fso = Nothing
