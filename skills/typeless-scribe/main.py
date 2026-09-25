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

from PIL import Image, ImageDraw
import pystray
from ui_manager import ui
from keyboard_hook import KeyboardManager
from backup_manager import restore_from_backup, sync_to_backup

# 自動災難復原防護：若本地缺少關鍵設定，從 Dropbox 鏡像還原；啟動時靜默鏡像備份
restore_from_backup()
sync_to_backup()


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
    print("[Tray] 使用者點擊『🎓 測試 7 月學生名單提醒...』選單", flush=True)
    ui.msg_queue.put('open_student_reminder')

def on_open_dictionary_notepad(icon, item):
    import subprocess
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dictionary.txt')
    subprocess.Popen(['notepad.exe', dict_path])

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
            pystray.MenuItem('🎓 測試 7 月學生名單提醒...', on_test_student_reminder),
            pystray.MenuItem('API 設定 (API Keys)', on_open_settings),
            pystray.MenuItem('📖 操作說明與快捷鍵 (README)', on_open_help),
            pystray.MenuItem('離開 (Quit)', on_quit),
            pystray.MenuItem('🔄 重新啟動 (Restart)', on_restart)
        )
    )
    icon.run()

from config_manager import get_api_key

def main():
    print("=" * 50)
    print(" 🚀 NoType 語音輔助常駐程式已啟動")
    print("=" * 50)
    print("操作方式：")
    print("  【錄音主熱鍵：鍵盤右手邊 Alt 鍵】(底層物理阻截防選單奪焦)")
    print("    1. 單擊切換 (Toggle)      : 按一下開始錄音，按第二下停止並貼上")
    print("    2. 長按說話 (Hold-to-Talk): 按住右 Alt 說話，放開即停止並貼上")
    print("  【錄音備用熱鍵：F9 鍵】")
    print("    1. 單擊切換 (Toggle)      : 按一下開始錄音，再按一下停止並貼上")
    print("  【反白修飾與糾錯熱鍵】")
    print("    1. F8 鍵                   : 桌面全域反白選取文字重新修飾")
    print("    2. Shift + F8 鍵           : 桌面全域極速糾錯教學與詞彙學習")
    print("=" * 50)
    
    if not get_api_key():
        print("⚠️ 尚未設定 API Key！請在螢幕右下角系統匣找到藍色圓形圖示，按右鍵選擇「API 設定」來輸入。")
    else:
        print("✅ API Key 已從設定檔自動載入，系統準備就緒！")

    # 啟動全域熱鍵監聽
    kb_manager = KeyboardManager()
    kb_manager.start()

    # 在背景執行緒啟動系統匣
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    # 每年 7 月新學年度學生名單提醒巡檢執行緒 (啟動後 2 秒與每 12 小時檢查)
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
