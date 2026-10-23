import sys
import threading
import os
import ctypes

# 將所有的輸出導向至 run_log.txt，方便我們在背景模式 (pythonw) 時除錯
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_log.txt')
sys.stdout = open(log_path, 'a', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

# 0. Windows 單實例互斥鎖防護 (防止重複啟動導致鍵盤鉤子重複監聽、文字重複貼上兩次)
kernel32 = ctypes.windll.kernel32
_mutex = kernel32.CreateMutexW(None, False, "Local\\NoType_Typeless_Scribe_SingleInstance_Mutex")
last_err = kernel32.GetLastError()
if last_err in (183, 5):  # ERROR_ALREADY_EXISTS or ERROR_ACCESS_DENIED
    print(f"\n[Mutex] 偵測到已有另一實例執行中或互斥鎖衝突 (LastError={last_err})，程式退出。")
    if _mutex:
        kernel32.CloseHandle(_mutex)
    os._exit(0)

# 0.1 物理安全鎖 3：將 NoType 行程優先級提升為 HIGH_PRIORITY_CLASS (0x00000080)
# 確保作為全域鍵盤監聽與即時語音輸入守護進程，永遠優先於背景轉檔/排查等批次任務，物理杜絕 LowLevelHooksTimeout 逾時拔鉤
try:
    from ctypes import wintypes
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetPriorityClass.restype = wintypes.BOOL
    h_proc = kernel32.GetCurrentProcess()
    if kernel32.SetPriorityClass(h_proc, 0x00000080):
        print("[Priority] NoType 行程優先權已成功提升為 HIGH_PRIORITY_CLASS (即時優先響應)")
    else:
        print(f"[Priority] 提升優先權失敗: Error={kernel32.GetLastError()}")
except Exception as e:
    print(f"[Priority] 提升優先權異常: {e}")

from PIL import Image, ImageDraw
import pystray
from ui_manager import ui
from keyboard_hook import KeyboardManager
from backup_manager import sync_bidirectional, sync_device_diagnostics
import config_manager

# 自動雙向同步與災難復原防護：啟動時智慧合併雲端與本地字典/自癒修正，並同步筆電診斷日誌
sync_bidirectional()
sync_device_diagnostics()



def create_image():
    # 生成一個簡單的藍色圓形圖示代表 NoType
    image = Image.new('RGB', (64, 64), color='white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([16, 16, 48, 48], fill='#3498db')
    return image

def on_open_history(icon, item):
    ui.msg_queue.put('open_history')

def on_open_settings(icon, item):
    ui.msg_queue.put('open_settings')

def on_open_help(icon, item):
    ui.msg_queue.put('open_help')

def on_open_dictionary(icon, item):
    ui.msg_queue.put('open_dictionary')

def on_import_dictionary(icon, item):
    ui.msg_queue.put('import_dictionary')

def on_export_dictionary(icon, item):
    ui.msg_queue.put('export_dictionary')

def on_test_student_reminder(icon, item):
    print("[Tray] 使用者點擊『🎓 學生名單例行檢核 (6月)...』選單", flush=True)
    ui.msg_queue.put('open_student_reminder')

def on_open_dictionary_notepad(icon, item):
    import subprocess
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dictionary.txt')
    subprocess.Popen(['notepad.exe', dict_path])

kb_manager = None

def on_rehook(icon, item):
    global kb_manager
    print("[Tray] 使用者點擊『⚡ 重新掛載鍵盤鉤子』，執行即時自癒...", flush=True)
    if kb_manager:
        kb_manager.restart_listener()
        ui.toast("⚡ 鍵盤鉤子已重新掛載就緒", is_error=False, duration=2000)

def on_restart(icon, item):
    global _mutex
    import subprocess
    import time
    
    bat_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'start_admin.bat'))
    if not os.path.exists(bat_path):
        bat_path = r"E:\AI_Work\NoType\start_admin.bat"
        
    try:
        if _mutex:
            kernel32.CloseHandle(_mutex)
            _mutex = None
    except Exception:
        pass
        
    try:
        icon.stop()
    except Exception:
        pass
        
    try:
        os.startfile(bat_path)
    except Exception:
        subprocess.Popen(['cmd.exe', '/c', bat_path], shell=True)
        
    time.sleep(0.1)
    os._exit(0)

def on_quit(icon, item):
    icon.stop()
    ui.msg_queue.put('quit')

def run_tray():
    icon = pystray.Icon(
        'NoType', 
        create_image(), 
        title='NoType 語音輔助', 
        menu=pystray.Menu(
            pystray.MenuItem('歷史紀錄 (History)', on_open_history, default=True),
            pystray.MenuItem('專屬字典管理 (Dictionary)', pystray.Menu(
                pystray.MenuItem('開啟字典管理面板', on_open_dictionary, default=True),
                pystray.MenuItem('📥 匯入字典 (Import)...', on_import_dictionary),
                pystray.MenuItem('📤 匯出字典 (Export)...', on_export_dictionary),
                pystray.MenuItem('📝 記事本直接編輯', on_open_dictionary_notepad),
            )),
            pystray.MenuItem(
                '🎓 學生名單例行檢核 (6月)...', 
                on_test_student_reminder,
                visible=lambda item: config_manager.should_prompt_student_reminder()
            ),
            pystray.MenuItem('API 設定 (API Keys)', on_open_settings),
            pystray.MenuItem('📖 操作說明與快捷鍵 (README)', on_open_help),
            pystray.MenuItem('⚡ 重新掛載鍵盤鉤子 (Re-hook)', on_rehook),
            pystray.MenuItem('🔄 重新啟動 (Restart)', on_restart),
            pystray.MenuItem('離開 (Quit)', on_quit)
        )
    )
    icon.run()

from config_manager import get_api_key

def main():
    print("=" * 50)
    print(" 🚀 NoType 語音輔助常駐程式已啟動")
    print("=" * 50)
    print("操作方式：")
    print("  【1. 語音輸入主熱鍵：~ 波浪鍵 或 鍵盤右手邊 Alt】(底層物理阻截防選單奪焦)")
    print("    • 單擊切換 (Toggle)      : 按一下開始錄音，按第二下停止並貼上")
    print("    • 長按說話 (Hold-to-Talk): 按住說話，放開即停止並貼上 (Shift + ~ 正常輸入符號)")
    print("  【2. 極速糾錯教學熱鍵 (重要性第二！)】")
    print("    • Ctrl + ~               : 桌面全域極速糾錯教學與詞彙學習 (筆電桌機通用免 Fn)")
    print("  【3. 桌面反白修飾熱鍵】")
    print("    • Alt + ~ 鍵             : 桌面全域反白選取文字重新修飾 (免 Fn、徹底根除飛航衝突)")
    print("=" * 50)
    
    if not get_api_key():
        print("⚠️ 尚未設定 API Key！請在螢幕右下角系統匣找到藍色圓形圖示，按右鍵選擇「API 設定」來輸入。")
    else:
        print("✅ API Key 已從設定檔自動載入，系統準備就緒！")

    # 啟動全域熱鍵監聽
    global kb_manager
    kb_manager = KeyboardManager()
    kb_manager.start()

    # 在背景執行緒啟動系統匣
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    # 每年 6 月新學年度學生名單提醒巡檢執行緒 (啟動後 2 秒與每 12 小時檢查)
    def _student_reminder_worker():
        import time
        time.sleep(2)
        ui.msg_queue.put('check_student_reminder')
        while True:
            time.sleep(3600 * 12)
            ui.msg_queue.put('check_student_reminder')

    threading.Thread(target=_student_reminder_worker, daemon=True).start()

    # 啟動 Tkinter 訊息迴圈 (必須位於主執行緒)
    ui.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程式已結束")
        sys.exit(0)
