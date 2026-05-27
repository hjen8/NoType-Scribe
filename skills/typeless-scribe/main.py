import sys
import threading
import os

# 將所有的輸出導向至 run_log.txt，方便我們在背景模式 (pythonw) 時除錯
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_log.txt')
sys.stdout = open(log_path, 'a', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

from PIL import Image, ImageDraw
import pystray
from ui_manager import ui
from keyboard_hook import KeyboardManager

def create_image():
    # 生成一個簡單的藍色圓形圖示代表 NoType
    image = Image.new('RGB', (64, 64), color='white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([16, 16, 48, 48], fill='#3498db')
    return image

def on_open_settings(icon, item):
    ui.msg_queue.put('open_settings')

def on_open_dictionary(icon, item):
    import subprocess
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dictionary.txt')
    if not os.path.exists(dict_path):
        with open(dict_path, 'w', encoding='utf-8') as f:
            f.write("# 在此輸入您的專屬詞彙，每行一個。\n# AI 會優先參考這些詞彙來修正語音辨識。\n# 例如：\n# 喀斯特地形\n# 莫氏不連續面\n# 羅吉斯迴歸\n# 探究與實作\n")
    # 使用記事本開啟
    subprocess.Popen(['notepad.exe', dict_path])

def on_quit(icon, item):
    icon.stop()
    ui.msg_queue.put('quit')

def run_tray():
    icon = pystray.Icon(
        'NoType', 
        create_image(), 
        title='NoType 語音輔助', 
        menu=pystray.Menu(
            pystray.MenuItem('設定 (Settings)', on_open_settings, default=True),
            pystray.MenuItem('編輯專屬字典 (Dictionary)', on_open_dictionary),
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
    print("  按第一下 <F9> 鍵 : 開始錄音 (畫面右下角會提示)")
    print("  按第二下 <F9> 鍵 : 停止錄音，並在游標處貼上 AI 修飾後的純文字")
    print("=" * 50)
    
    if not get_api_key():
        print("⚠️ 尚未設定 API Key！請在螢幕右下角系統匣找到藍色圓形圖示，按右鍵選擇「設定」來輸入。")
    else:
        print("✅ API Key 已從設定檔自動載入，系統準備就緒！")

    # 啟動全域熱鍵監聽
    kb_manager = KeyboardManager()
    kb_manager.start()

    # 在背景執行緒啟動系統匣
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    # 啟動 Tkinter 訊息迴圈 (必須位於主執行緒)
    ui.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程式已結束")
        sys.exit(0)
