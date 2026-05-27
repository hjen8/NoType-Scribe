# Typeless Scribe (NoType)

## 專案知識沉澱 (Knowledge Sedimentation)

### ⚠️ 開機自動啟動機制的重要提醒
本專案的「開機自動隱藏啟動」高度依賴 Windows 工作排程器 (Task Scheduler) 與 VBS 腳本的配合。
- **核心路徑**：工作排程器任務 `\NoType_AutoStart` 綁定執行 `run_hidden.vbs`。
- **啟動鏈條**：`Task Scheduler` -> `run_hidden.vbs` -> `start_admin.bat` -> `pythonw.exe main.py`
- **防呆警告**：在執行「收工清理 (Cleanup)」時，**絕對不可將 `run_hidden.vbs` 或 `start_admin.bat` 視為無用暫存檔刪除**。若將其移除，將會導致隔日開機時工作排程器找不到檔案而跳出 Script 錯誤。
