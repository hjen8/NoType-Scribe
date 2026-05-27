import tkinter as tk
import queue
from config_manager import get_api_key, set_api_key

class UIManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # 隱藏主視窗
        self.msg_queue = queue.Queue()
        self.floating_win = None
        self.settings_win = None

    def show_floating(self):
        if self.floating_win:
            return
        
        self.floating_win = tk.Toplevel(self.root)
        self.floating_win.overrideredirect(True)
        self.floating_win.attributes("-topmost", True)
        self.floating_win.configure(bg="#2c3e50")
        
        tk.Label(
            self.floating_win, 
            text="🎤 錄音中...", 
            font=("Microsoft JhengHei", 14, "bold"), 
            fg="white", 
            bg="#2c3e50", 
            padx=10, 
            pady=5
        ).pack()
        
        # 鎖定在主螢幕右下角
        sw = self.floating_win.winfo_screenwidth()
        sh = self.floating_win.winfo_screenheight()
        w, h = 150, 40
        self.floating_win.geometry(f"{w}x{h}+{sw-w-50}+{sh-h-100}")

    def hide_floating(self):
        if self.floating_win:
            self.floating_win.destroy()
            self.floating_win = None

    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
            
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("NoType 設定")
        self.settings_win.geometry("400x150")
        self.settings_win.attributes("-topmost", True)
        
        tk.Label(self.settings_win, text="Groq API Key:", font=("Microsoft JhengHei", 10)).pack(pady=10)
        
        entry = tk.Entry(self.settings_win, width=40, show="*")
        entry.pack(pady=5)
        entry.insert(0, get_api_key())
        
        def save():
            set_api_key(entry.get())
            self.settings_win.destroy()
            print("API Key 已儲存")
            
        tk.Button(self.settings_win, text="儲存", command=save, font=("Microsoft JhengHei", 10)).pack(pady=10)

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if msg == 'show_floating':
                    self.show_floating()
                elif msg == 'hide_floating':
                    self.hide_floating()
                elif msg == 'open_settings':
                    self.open_settings()
                elif msg == 'quit':
                    self.root.quit()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
        
    def start(self):
        self.root.after(100, self.process_queue)
        self.root.mainloop()

# 建立全域單例供其他執行緒呼叫
ui = UIManager()
