import tkinter as tk
import queue
import os
import subprocess
import pyperclip
from config_manager import get_api_key, set_api_key

class UIManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # 隱藏主視窗
        self.msg_queue = queue.Queue()
        self.floating_win = None
        self.settings_win = None
        self.history_win = None
        self.dictionary_win = None
        self.help_win = None
        self.toast_wins = []

    def show_toast(self, text, bg="#c0392b", duration=3500):
        try:
            toast = tk.Toplevel(self.root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg=bg)
            
            lbl = tk.Label(
                toast, 
                text=text, 
                font=("Microsoft JhengHei", 11, "bold"), 
                fg="white", 
                bg=bg, 
                padx=15, 
                pady=10,
                justify="left",
                wraplength=350
            )
            lbl.pack()
            
            toast.update_idletasks()
            sw = toast.winfo_screenwidth()
            sh = toast.winfo_screenheight()
            w = toast.winfo_reqwidth()
            h = toast.winfo_reqheight()
            
            # 顯示在主螢幕右下角
            offset_y = 100 + (len(self.toast_wins) * (h + 10))
            toast.geometry(f"{w}x{h}+{sw - w - 40}+{sh - offset_y}")
            
            self.toast_wins.append(toast)
            
            def close():
                if toast in self.toast_wins:
                    self.toast_wins.remove(toast)
                try:
                    toast.destroy()
                except Exception:
                    pass
                    
            toast.after(duration, close)
        except Exception as e:
            print(f"[Toast] Failed: {e}")

    def toast(self, text, is_error=True, duration=3500):
        bg = "#c0392b" if is_error else "#27ae60"
        self.msg_queue.put(('show_toast', text, bg, duration))

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
            self.settings_win.focus_force()
            return
            
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("NoType API 設定 (API Keys)")
        self.settings_win.attributes("-topmost", True)
        
        w, h = 480, 270
        sw = self.settings_win.winfo_screenwidth()
        sh = self.settings_win.winfo_screenheight()
        self.settings_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        from config_manager import get_gemini_api_key, set_gemini_api_key
        
        # 1. Groq API Keys
        tk.Label(
            self.settings_win, 
            text="Groq API Key (主要，支援多組以逗號或空格分隔自動輪替):", 
            font=("Microsoft JhengHei", 9, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 2))
        
        entry_groq = tk.Entry(self.settings_win, width=54, show="*")
        entry_groq.pack(padx=20, pady=2)
        entry_groq.insert(0, get_api_key())
        entry_groq.focus_set()
        
        # 2. Gemini API Key
        tk.Label(
            self.settings_win, 
            text="Gemini API Key (選填，Groq 額度全滿時之自動備援):", 
            font=("Microsoft JhengHei", 9, "bold")
        ).pack(anchor="w", padx=20, pady=(12, 2))
        
        entry_gemini = tk.Entry(self.settings_win, width=54, show="*")
        entry_gemini.pack(padx=20, pady=2)
        entry_gemini.insert(0, get_gemini_api_key())
        
        def save():
            set_api_key(entry_groq.get().strip())
            set_gemini_api_key(entry_gemini.get().strip())
            self.settings_win.destroy()
            print("API Keys saved")
            self.toast("✅ API 金鑰設定已更新儲存！", is_error=False, duration=2500)
            
        btn_frame = tk.Frame(self.settings_win)
        btn_frame.pack(pady=18)
        tk.Button(
            btn_frame, 
            text=" 儲存並啟用 ", 
            command=save, 
            bg="#27ae60", 
            fg="white", 
            font=("Microsoft JhengHei", 10, "bold"),
            padx=10,
            pady=2
        ).pack()

    # =====================================================
    #  歷史紀錄面板 (Dark Theme History Panel)
    # =====================================================
    
    # 色彩常數
    BG_DARK   = "#1e1e1e"
    BG_CARD   = "#2a2a2a"
    BG_HOVER  = "#333333"
    FG_TEXT   = "#e0e0e0"
    FG_DIM    = "#888888"
    FG_TIME   = "#aaaaaa"
    TAG_GREEN = "#27ae60"
    TAG_RED   = "#c0392b"
    BTN_BG    = "#3a3a3a"
    BTN_HOVER = "#4a4a4a"
    
    def open_history(self):
        from history_manager import get_all, get_count
        
        if self.history_win and self.history_win.winfo_exists():
            self.history_win.lift()
            self.history_win.focus_force()
            self._refresh_history()
            return
        
        self.history_win = tk.Toplevel(self.root)
        self.history_win.title("NoType 歷史紀錄")
        self.history_win.configure(bg=self.BG_DARK)
        self.history_win.attributes("-topmost", True)
        
        win_w, win_h = 720, 520
        sw = self.history_win.winfo_screenwidth()
        sh = self.history_win.winfo_screenheight()
        self.history_win.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.history_win.minsize(600, 400)
        
        # 標題列
        header = tk.Frame(self.history_win, bg=self.BG_DARK)
        header.pack(fill="x", padx=20, pady=(15, 5))
        
        tk.Label(
            header, text="歷史紀錄", 
            font=("Microsoft JhengHei", 16, "bold"),
            fg=self.FG_TEXT, bg=self.BG_DARK
        ).pack(side="left")
        
        self._history_count_label = tk.Label(
            header, text="",
            font=("Microsoft JhengHei", 10),
            fg=self.FG_DIM, bg=self.BG_DARK
        )
        self._history_count_label.pack(side="left", padx=(12, 0))
        
        # 重新整理按鈕
        tk.Button(
            header, text=" 重新整理 ",
            font=("Microsoft JhengHei", 9),
            bg=self.BTN_BG, fg=self.FG_TEXT,
            activebackground=self.BTN_HOVER, activeforeground=self.FG_TEXT,
            bd=0, padx=8, pady=2,
            command=self._refresh_history
        ).pack(side="right")
        
        # 分隔線
        tk.Frame(self.history_win, bg="#444444", height=1).pack(fill="x", padx=20, pady=(5, 0))
        
        # 可捲動區域
        scroll_container = tk.Frame(self.history_win, bg=self.BG_DARK)
        scroll_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(scroll_container, bg=self.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        
        self._history_frame = tk.Frame(canvas, bg=self.BG_DARK)
        self._history_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=self._history_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 滑鼠滾輪綁定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self._history_canvas = canvas
        
        # 視窗關閉時解綁滾輪
        def on_close():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            self.history_win.destroy()
            self.history_win = None
        self.history_win.protocol("WM_DELETE_WINDOW", on_close)
        
        self._refresh_history()
    
    def _refresh_history(self):
        from history_manager import get_all, get_count
        
        if not self.history_win or not self.history_win.winfo_exists():
            return
        
        # 清空舊卡片
        for widget in self._history_frame.winfo_children():
            widget.destroy()
        
        records = get_all()
        count = get_count()
        self._history_count_label.config(text=f"共 {count} 筆")
        
        if not records:
            tk.Label(
                self._history_frame, 
                text="\n\n  按下 <右側 Alt> 開始錄音，歷史紀錄將在此顯示  \n\n",
                font=("Microsoft JhengHei", 11),
                fg=self.FG_DIM, bg=self.BG_DARK
            ).pack(pady=60)
            return
        
        for rec in records:
            self._create_history_card(rec)
    
    def _create_history_card(self, rec):
        card = tk.Frame(self._history_frame, bg=self.BG_CARD, padx=12, pady=10)
        card.pack(fill="x", padx=10, pady=3)
        
        # --- 第一行：時間戳 + 狀態標籤 + 秒數 ---
        top_row = tk.Frame(card, bg=self.BG_CARD)
        top_row.pack(fill="x")
        
        # 時間戳
        tk.Label(
            top_row, text=rec.timestamp,
            font=("Consolas", 9),
            fg=self.FG_TIME, bg=self.BG_CARD
        ).pack(side="left")
        
        # 狀態標籤
        if rec.status == "success":
            tag_text = " AI 整理 "
            tag_bg = self.TAG_GREEN
        else:
            tag_text = " 轉換失敗 "
            tag_bg = self.TAG_RED
        
        tag_label = tk.Label(
            top_row, text=tag_text,
            font=("Microsoft JhengHei", 8, "bold"),
            fg="white", bg=tag_bg,
            padx=4, pady=1
        )
        tag_label.pack(side="left", padx=(8, 0))
        
        # 右側按鈕區
        btn_frame = tk.Frame(top_row, bg=self.BG_CARD)
        btn_frame.pack(side="right")
        
        # 秒數
        tk.Label(
            btn_frame, text=f"{rec.duration_sec} 秒",
            font=("Consolas", 9),
            fg=self.FG_DIM, bg=self.BG_CARD
        ).pack(side="left", padx=(0, 10))
        
        # 1. 複製按鈕 (最高頻使用，置於最左側)：所見即所得，優先取修飾文字，若無則取逐字稿
        text_to_copy = (rec.refined_text.strip() if (rec.refined_text and rec.refined_text.strip()) 
                        else (rec.raw_text.strip() if rec.raw_text else ""))
        copy_btn = tk.Button(
            btn_frame, text=" 📋 ",
            font=("Segoe UI Emoji", 10),
            bg=self.BTN_BG, fg=self.FG_TEXT,
            activebackground=self.BTN_HOVER, activeforeground="white",
            bd=0, padx=4, pady=0,
            command=lambda t=text_to_copy: self._copy_text(t)
        )
        copy_btn.pack(side="left", padx=2)
        
        # 2. 重播按鈕
        audio_path = rec.audio_path
        play_btn = tk.Button(
            btn_frame, text=" ▷ ",
            font=("Consolas", 10),
            bg=self.BTN_BG, fg=self.FG_TEXT,
            activebackground=self.BTN_HOVER, activeforeground="white",
            bd=0, padx=4, pady=0,
            command=lambda p=audio_path: self._play_audio(p)
        )
        play_btn.pack(side="left", padx=2)
        
        # 3. 重新辨識按鈕
        rerun_btn = tk.Button(
            btn_frame, text=" 🔄 ",
            font=("Segoe UI Emoji", 10),
            bg=self.BTN_BG, fg=self.FG_TEXT,
            activebackground=self.BTN_HOVER, activeforeground="white",
            bd=0, padx=4, pady=0,
            command=lambda r=rec: self._reprocess_record(r)
        )
        rerun_btn.pack(side="left", padx=2)
        
        # 4. 糾錯學習按鈕
        edit_btn = tk.Button(
            btn_frame, text=" ✏️ ",
            font=("Segoe UI Emoji", 10),
            bg=self.BTN_BG, fg=self.FG_TEXT,
            activebackground=self.BTN_HOVER, activeforeground="white",
            bd=0, padx=4, pady=0,
            command=lambda r=rec: self._open_correction_dialog(r)
        )
        edit_btn.pack(side="left", padx=2)
        
        # --- 第二行：修飾後文字 ---
        display_text = rec.refined_text if rec.refined_text else rec.raw_text
        # 截斷過長文字
        if len(display_text) > 120:
            display_text = display_text[:120] + "..."
        
        tk.Label(
            card, text=display_text,
            font=("Microsoft JhengHei", 10),
            fg=self.FG_TEXT, bg=self.BG_CARD,
            anchor="w", justify="left",
            wraplength=620
        ).pack(fill="x", pady=(6, 0))
    
    def _reprocess_record(self, rec):
        if not rec.audio_path or not os.path.exists(rec.audio_path):
            self.toast("⚠️ 原始音檔不存在或已被清除", is_error=True, duration=2500)
            return
            
        self.toast("⏳ 正在以最新詞庫重新辨識中...", is_error=False, duration=2500)
        
        import threading
        def worker():
            try:
                from groq_api import transcribe_audio, generate_notes
                raw = transcribe_audio(rec.audio_path)
                if not raw or not raw.strip():
                    self.toast("⚠️ 未偵測到有效語音", is_error=True, duration=2500)
                    return
                refined = generate_notes(raw)
                rec.raw_text = raw.strip()
                rec.refined_text = refined.strip() if (refined and refined.strip()) else raw.strip()
                rec.status = "success"
                rec.error_msg = ""
                self.msg_queue.put('refresh_history')
                self.toast("✅ 重新辨識完成！", is_error=False, duration=2500)
            except Exception as e:
                self.toast(f"❌ 重新辨識失敗: {e}", is_error=True, duration=3500)
                
        threading.Thread(target=worker, daemon=True).start()

    def _open_correction_dialog(self, rec):
        dialog = tk.Toplevel(self.root)
        dialog.title("NoType 糾錯與自適應學習")
        dialog.configure(bg=self.BG_DARK)
        dialog.attributes("-topmost", True)
        
        win_w, win_h = 520, 390
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        
        # 標題
        tk.Label(
            dialog, text="✏️ 糾錯與自適應學習",
            font=("Microsoft JhengHei", 13, "bold"),
            fg=self.FG_TEXT, bg=self.BG_DARK
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        # 整句修改
        tk.Label(
            dialog, text="1. 修正後的完整文字 (更新此卡片顯示):",
            font=("Microsoft JhengHei", 9, "bold"),
            fg=self.FG_TIME, bg=self.BG_DARK
        ).pack(anchor="w", padx=20, pady=(8, 2))
        
        entry_full = tk.Entry(dialog, width=58, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_full.pack(padx=20, pady=2)
        curr_text = rec.refined_text if rec.refined_text else rec.raw_text
        entry_full.insert(0, curr_text)
        entry_full.focus_set()
        
        # 分隔線
        tk.Frame(dialog, bg="#444444", height=1).pack(fill="x", padx=20, pady=12)
        
        tk.Label(
            dialog, text="2. 教 AI 專屬詞彙 (自動建立學習記憶，未來永久自動校正):",
            font=("Microsoft JhengHei", 9, "bold"),
            fg="#f39c12", bg=self.BG_DARK
        ).pack(anchor="w", padx=20, pady=(2, 6))
        
        pair_frame = tk.Frame(dialog, bg=self.BG_DARK)
        pair_frame.pack(fill="x", padx=20)
        
        # 左：聽錯的詞
        left_col = tk.Frame(pair_frame, bg=self.BG_DARK)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(left_col, text="AI 聽錯的詞 (選填):", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK).pack(anchor="w")
        entry_wrong = tk.Entry(left_col, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_wrong.pack(fill="x", pady=2)
        
        # 右：真正要表達的詞
        right_col = tk.Frame(pair_frame, bg=self.BG_DARK)
        right_col.pack(side="right", fill="x", expand=True, padx=(10, 0))
        tk.Label(right_col, text="真正正確的詞 (自動存入字典):", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK).pack(anchor="w")
        entry_correct = tk.Entry(right_col, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_correct.pack(fill="x", pady=2)
        
        hint_lbl = tk.Label(
            dialog, 
            text="💡 例如：聽錯「實心營」➔ 正確「石星瑩」，儲存後未來再說這句話就會 100% 正確！",
            font=("Microsoft JhengHei", 8),
            fg="#95a5a6", bg=self.BG_DARK
        )
        hint_lbl.pack(anchor="w", padx=20, pady=(8, 15))
        
        # 按鈕區
        def save():
            from learning_manager import add_correction
            new_sentence = entry_full.get().strip()
            if new_sentence:
                rec.refined_text = new_sentence
                rec.status = "success"
                
            wrong = entry_wrong.get().strip()
            correct = entry_correct.get().strip()
            if correct:
                add_correction(wrong, correct)
                self.toast(f"✅ 已學習專屬詞彙：{correct}！", is_error=False, duration=2500)
            else:
                self.toast("✅ 歷史紀錄文字已更新！", is_error=False, duration=2000)
                
            dialog.destroy()
            self._refresh_history()
            
        btn_box = tk.Frame(dialog, bg=self.BG_DARK)
        btn_box.pack(pady=(5, 15))
        
        tk.Button(
            btn_box, text=" 儲存並學習 ", command=save,
            font=("Microsoft JhengHei", 10, "bold"),
            bg="#27ae60", fg="white", bd=0, padx=12, pady=4
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_box, text=" 取消 ", command=dialog.destroy,
            font=("Microsoft JhengHei", 10),
            bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=10, pady=4
        ).pack(side="left", padx=10)
    
    def _play_audio(self, audio_path):
        if audio_path and os.path.exists(audio_path):
            try:
                import winsound
                # 優先使用 Windows 內建非同步播放，背景播放無彈窗
                winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                try:
                    os.startfile(audio_path)
                except Exception as e:
                    self.toast(f"無法播放音檔: {e}", is_error=True, duration=3000)
        else:
            self.toast("音檔不存在或已被清除", is_error=True, duration=2500)
    
    def _copy_text(self, text):
        if not text or not str(text).strip():
            self.toast("⚠️ 該紀錄無有效文字可複製", is_error=True, duration=2500)
            return
        target = str(text).strip()
        try:
            pyperclip.copy(target)
            # 雙重防護：同步寫入 Tkinter 剪貼簿，避免 Windows 剪貼簿鎖定導致的寫入失敗
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(target)
                self.root.update()
            except Exception:
                pass
            self.toast("✅ 已複製到剪貼簿！", is_error=False, duration=1500)
        except Exception as e:
            self.toast(f"複製失敗: {e}", is_error=True, duration=2500)

    def open_quick_learn(self, wrong_text="", on_saved=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("NoType 極速糾錯學習")
        dialog.configure(bg=self.BG_DARK)
        dialog.attributes("-topmost", True)
        
        win_w, win_h = 460, 290
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        
        tk.Label(
            dialog, text="✏️ 極速教學與詞彙學習",
            font=("Microsoft JhengHei", 12, "bold"),
            fg=self.FG_TEXT, bg=self.BG_DARK
        ).pack(anchor="w", padx=20, pady=(12, 4))
        
        # 聽錯的詞
        row1 = tk.Frame(dialog, bg=self.BG_DARK)
        row1.pack(fill="x", padx=20, pady=3)
        tk.Label(row1, text="聽錯的詞：", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK, width=10, anchor="w").pack(side="left")
        entry_wrong = tk.Entry(row1, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_wrong.pack(side="left", fill="x", expand=True)
        if wrong_text:
            entry_wrong.insert(0, wrong_text)
            
        # 正確的詞
        row2 = tk.Frame(dialog, bg=self.BG_DARK)
        row2.pack(fill="x", padx=20, pady=4)
        tk.Label(row2, text="正確的詞：", font=("Microsoft JhengHei", 9, "bold"), fg="#f39c12", bg=self.BG_DARK, width=10, anchor="w").pack(side="left")
        entry_correct = tk.Entry(row2, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_correct.pack(side="left", fill="x", expand=True)
        entry_correct.focus_set()
        
        # 提示標籤
        hint_text = "💡「僅本次替換」只修改當前選取文字；「永久學習」會一併存入字典供日後自動校正"
        lbl_hint = tk.Label(
            dialog, 
            text=hint_text, 
            font=("Microsoft JhengHei", 8),
            fg="#95a5a6", bg=self.BG_DARK
        )
        lbl_hint.pack(anchor="w", padx=20, pady=(6, 15))
        
        # 動作 1：僅本次替換 (不存入字典)
        def replace_once(event=None):
            correct = entry_correct.get().strip()
            dialog.destroy()
            if correct:
                self.toast(f"✅ 已替換文字為「{correct}」（未存入字典）！", is_error=False, duration=2000)
                if on_saved:
                    on_saved(correct)
                    
        # 動作 2：永久學習並替換
        def replace_and_learn(event=None):
            wrong = entry_wrong.get().strip()
            correct = entry_correct.get().strip()
            dialog.destroy()
            if correct:
                from learning_manager import add_correction
                add_correction(wrong, correct)
                self.toast(f"✅ 已替換並永久學習新詞「{correct}」！", is_error=False, duration=2500)
                if on_saved:
                    on_saved(correct)
            
        def cancel(event=None):
            dialog.destroy()
            
        # 鍵盤快捷鍵綁定
        dialog.bind("<Return>", replace_once)
        dialog.bind("<Shift-Return>", replace_and_learn)
        dialog.bind("<Escape>", cancel)
        
        # 三大按鈕區
        btn_box = tk.Frame(dialog, bg=self.BG_DARK)
        btn_box.pack(pady=4)
        
        # 1. 僅本次替換
        tk.Button(
            btn_box, text=" 僅本次替換 (Enter) ", command=replace_once,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#2980b9", fg="white", bd=0, padx=10, pady=4
        ).pack(side="left", padx=6)
        
        # 2. 永久學習並替換
        tk.Button(
            btn_box, text=" 永久學習並替換 (Shift+Enter) ", command=replace_and_learn,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#27ae60", fg="white", bd=0, padx=10, pady=4
        ).pack(side="left", padx=6)
        
        # 3. 取消
        tk.Button(
            btn_box, text=" 取消 (Esc) ", command=cancel,
            font=("Microsoft JhengHei", 9),
            bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=10, pady=4
        ).pack(side="left", padx=6)

    # =====================================================
    #  操作說明與快捷鍵指南 (Help / README)
    # =====================================================
    def open_help(self):
        if self.help_win and self.help_win.winfo_exists():
            self.help_win.lift()
            self.help_win.focus_force()
            return

        self.help_win = tk.Toplevel(self.root)
        self.help_win.title("NoType 快捷鍵與操作指南")
        self.help_win.configure(bg=self.BG_DARK)
        self.help_win.attributes("-topmost", True)

        w, h = 650, 580
        sw = self.help_win.winfo_screenwidth()
        sh = self.help_win.winfo_screenheight()
        self.help_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.help_win.resizable(False, False)

        header_frame = tk.Frame(self.help_win, bg="#1a252f", pady=12)
        header_frame.pack(fill="x")
        tk.Label(
            header_frame, text="📖 NoType 核心快捷鍵與操作指南", 
            font=("Microsoft JhengHei", 13, "bold"), fg="#3498db", bg="#1a252f"
        ).pack()
        tk.Label(
            header_frame, text="專為極速輸入、桌面反白修飾與自適應學習打造", 
            font=("Microsoft JhengHei", 9), fg="#bdc3c7", bg="#1a252f"
        ).pack(pady=(2, 0))

        content_box = tk.Frame(self.help_win, bg=self.BG_DARK, padx=20, pady=10)
        content_box.pack(fill="both", expand=True)

        def add_card(title, text, title_fg="#2ecc71"):
            card = tk.Frame(content_box, bg=self.BG_CARD, padx=14, pady=8, bd=1, relief="solid")
            card.pack(fill="x", pady=5)
            tk.Label(card, text=title, font=("Microsoft JhengHei", 10, "bold"), fg=title_fg, bg=self.BG_CARD).pack(anchor="w")
            tk.Label(card, text=text, font=("Microsoft JhengHei", 9), fg=self.FG_TEXT, bg=self.BG_CARD, justify="left", wraplength=590).pack(anchor="w", pady=(3, 0))

        add_card(
            "🎙️ 鍵盤右手邊 Alt 鍵 —— 語音輸入主熱鍵 (二合一智慧雙模態)",
            "• 底層物理阻截：在任何搜尋列、瀏覽器或輸入框按下，絕不觸發 Windows 選單奪焦。\n"
            "• 單擊切換 (Toggle)：按一下開始錄音，講完再按一下停止並自動貼上純文字。\n"
            "• 長按放開 (Hold-to-Talk)：大拇指按住說話，鬆開即停止並自動貼上純文字。",
            "#3498db"
        )
        add_card(
            "🎙️ F9 鍵 —— 備用全域語音輸入 (單擊切換)",
            "• 單擊切換 (Toggle)：適合筆電或偏好標準功能鍵者，按一下開始錄音，再按一下停止並貼上。",
            "#1abc9c"
        )
        add_card(
            "🔄 F8 鍵 —— 桌面全域反白選取重新修飾",
            "• 在任何編輯器、瀏覽器或記事本中反白選取文字。\n"
            "• 按下 F8，AI 會自動重新潤飾語句並原地替換覆蓋。",
            "#9b59b6"
        )
        add_card(
            "✏️ Shift + F8 鍵 —— 極速糾錯教學與詞彙學習",
            "• 反白錯字後按 Shift+F8 彈出糾錯浮窗，支援雙模式：\n"
            "  - 僅本次替換：單純替換當前選取文字，不存入字典\n"
            "  - 永久學習並替換：替換文字並同步寫入專屬字典，日後自動校正",
            "#2ecc71"
        )
        add_card(
            "⚙️ 系統匣選單 (藍色圖示按右鍵)",
            "• 歷史紀錄 (重播音檔 / 重新辨識)   • 專屬字典管理 (支援匯入/匯出)\n"
            "• API 設定 (Groq / Gemini)        • 🔄 重新啟動 (一鍵重拉服務)",
            "#f39c12"
        )

        btn_bar = tk.Frame(self.help_win, bg=self.BG_DARK, pady=10)
        btn_bar.pack(fill="x")

        def open_readme_file():
            import subprocess
            readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'README.md')
            if not os.path.exists(readme_path):
                readme_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'README.md'))
            subprocess.Popen(['notepad.exe', readme_path])

        tk.Button(
            btn_bar, text="📝 以記事本開啟完整 README.md", command=open_readme_file,
            font=("Microsoft JhengHei", 9, "bold"), bg="#34495e", fg="white", bd=0, padx=12, pady=5
        ).pack(side="left", padx=20)

        tk.Button(
            btn_bar, text=" 確定關閉 (Esc) ", command=self.help_win.destroy,
            font=("Microsoft JhengHei", 9, "bold"), bg="#2980b9", fg="white", bd=0, padx=15, pady=5
        ).pack(side="right", padx=20)

        self.help_win.bind("<Escape>", lambda e: self.help_win.destroy())
        self.help_win.bind("<Return>", lambda e: self.help_win.destroy())

    # =====================================================
    #  專屬字典管理面板 (Dictionary Manager & Import/Export)
    # =====================================================
    def open_dictionary(self):
        import dictionary_manager
        
        if self.dictionary_win and self.dictionary_win.winfo_exists():
            self.dictionary_win.lift()
            self.dictionary_win.focus_force()
            self._refresh_dictionary_list()
            return
            
        self.dictionary_win = tk.Toplevel(self.root)
        self.dictionary_win.title("NoType 專屬字典管理 (Dictionary Manager)")
        self.dictionary_win.configure(bg=self.BG_DARK)
        self.dictionary_win.attributes("-topmost", True)
        
        w, h = 540, 620
        sw = self.dictionary_win.winfo_screenwidth()
        sh = self.dictionary_win.winfo_screenheight()
        self.dictionary_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.dictionary_win.minsize(460, 480)
        
        def on_close():
            if self.dictionary_win:
                self.dictionary_win.destroy()
                self.dictionary_win = None
        self.dictionary_win.protocol("WM_DELETE_WINDOW", on_close)
        
        # --- Top Header ---
        header = tk.Frame(self.dictionary_win, bg=self.BG_DARK, padx=16, pady=12)
        header.pack(fill="x")
        
        title_lbl = tk.Label(
            header, text="📚 專屬自訂字典管理", 
            font=("Microsoft JhengHei", 14, "bold"), 
            fg=self.FG_TEXT, bg=self.BG_DARK
        )
        title_lbl.pack(anchor="w")
        
        self._dict_count_lbl = tk.Label(
            header, text="載入中...",
            font=("Microsoft JhengHei", 9),
            fg=self.FG_DIM, bg=self.BG_DARK
        )
        self._dict_count_lbl.pack(anchor="w", pady=(2, 0))
        
        # --- Search Bar & Quick Toggles ---
        search_box = tk.Frame(self.dictionary_win, bg=self.BG_DARK, padx=16, pady=4)
        search_box.pack(fill="x")
        
        tk.Label(
            search_box, text="🔍", font=("Microsoft JhengHei", 10),
            fg=self.FG_DIM, bg=self.BG_DARK
        ).pack(side="left")
        
        self._dict_search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_box, textvariable=self._dict_search_var,
            font=("Microsoft JhengHei", 10),
            bg=self.BG_CARD, fg=self.FG_TEXT, insertbackground="white", bd=1
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))
        
        def expand_all():
            if hasattr(self, '_dict_tree'):
                for c in self._dict_tree.get_children():
                    self._dict_tree.item(c, open=True)
                    
        def collapse_all():
            if hasattr(self, '_dict_tree'):
                for c in self._dict_tree.get_children():
                    self._dict_tree.item(c, open=False)
                    
        tk.Button(
            search_box, text=" ➕ 展開全部 ", command=expand_all,
            font=("Microsoft JhengHei", 8), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=6, pady=2
        ).pack(side="left", padx=2)
        tk.Button(
            search_box, text=" ➖ 全部收起 ", command=collapse_all,
            font=("Microsoft JhengHei", 8), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=6, pady=2
        ).pack(side="left", padx=2)
        
        # --- Treeview Frame ---
        tree_frame = tk.Frame(self.dictionary_win, bg=self.BG_CARD, padx=2, pady=2)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=6)
        
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")
        
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dict.Treeview",
            background=self.BG_CARD,
            foreground=self.FG_TEXT,
            fieldbackground=self.BG_CARD,
            font=("Microsoft JhengHei", 10),
            rowheight=26,
            borderwidth=0
        )
        style.map(
            "Dict.Treeview",
            background=[("selected", "#2980b9")],
            foreground=[("selected", "white")]
        )
        
        self._dict_tree = ttk.Treeview(
            tree_frame,
            show="tree",
            selectmode="browse",
            style="Dict.Treeview",
            yscrollcommand=scrollbar.set
        )
        self._dict_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._dict_tree.yview)
        
        self._dict_tree.tag_configure("category", font=("Microsoft JhengHei", 10, "bold"), foreground="#f1c40f")
        self._dict_tree.tag_configure("word", font=("Microsoft JhengHei", 9), foreground="#ecf0f1")
        
        # 單擊展開/收起樹狀目錄 (點一下展開，再點一下收起)
        def on_tree_click(event):
            item_id = self._dict_tree.identify_row(event.y)
            if not item_id:
                return
            # 若為分類節點 (父層為空)
            if not self._dict_tree.parent(item_id):
                element = self._dict_tree.identify_element(event.x, event.y)
                # 排除原生小箭頭 (原生小箭頭已被 Tkinter 自動切換)
                if element != "Treeitem.indicator":
                    is_open = self._dict_tree.item(item_id, "open")
                    self._dict_tree.item(item_id, open=not is_open)
                # 自動將底部新增分類選單切換至該分類
                cat_name = item_id.replace("cat_", "")
                if hasattr(self, '_dict_cat_var') and self._dict_cat_var:
                    self._dict_cat_var.set(cat_name)
            else:
                # 若點選為子項目詞彙，連動所屬分類
                vals = self._dict_tree.item(item_id, "values")
                if vals and len(vals) >= 2 and hasattr(self, '_dict_cat_var'):
                    self._dict_cat_var.set(vals[1])
                    
        self._dict_tree.bind("<ButtonRelease-1>", on_tree_click)
        
        # --- Quick Add / Delete Single Word Frame ---
        add_box = tk.Frame(self.dictionary_win, bg=self.BG_DARK, padx=16, pady=6)
        add_box.pack(fill="x")
        
        tk.Label(
            add_box, text="分類：", font=("Microsoft JhengHei", 9),
            fg=self.FG_DIM, bg=self.BG_DARK
        ).pack(side="left")
        
        self._dict_cat_var = tk.StringVar(value="地理、數學與學術名詞")
        self._dict_cat_menu = ttk.Combobox(
            add_box, textvariable=self._dict_cat_var,
            state="readonly", width=18, font=("Microsoft JhengHei", 9)
        )
        self._dict_cat_menu.pack(side="left", padx=(0, 8))
        
        self._dict_add_var = tk.StringVar()
        add_entry = tk.Entry(
            add_box, textvariable=self._dict_add_var,
            font=("Microsoft JhengHei", 10),
            bg=self.BG_CARD, fg=self.FG_TEXT, insertbackground="white", bd=1
        )
        add_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        
        def do_add_word(event=None):
            val = self._dict_add_var.get().strip()
            cat = self._dict_cat_var.get().strip() if hasattr(self, '_dict_cat_var') else "地理、數學與學術名詞"
            if val:
                if dictionary_manager.add_word(val, category=cat):
                    self.toast(f"✅ 已新增「{val}」至【{cat}】！", is_error=False, duration=2000)
                    self._dict_add_var.set("")
                    self._refresh_dictionary_list()
                    cat_id = f"cat_{cat}"
                    if self._dict_tree.exists(cat_id):
                        self._dict_tree.item(cat_id, open=True)
                        word_id = f"word_{cat}_{val}"
                        if self._dict_tree.exists(word_id):
                            self._dict_tree.selection_set(word_id)
                            self._dict_tree.see(word_id)
                else:
                    self.toast(f"⚠️ 詞彙「{val}」已存在或無效", is_error=True, duration=2500)
                    
        add_entry.bind("<Return>", do_add_word)
        
        tk.Button(
            add_box, text=" ➕ 新增詞彙 ", command=do_add_word,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#27ae60", fg="white", bd=0, padx=8, pady=3
        ).pack(side="left")
        
        def do_delete_word():
            sel = self._dict_tree.selection()
            if not sel:
                self.toast("⚠️ 請先在樹狀清單中點選要刪除的詞彙", is_error=True, duration=2500)
                return
            item_id = sel[0]
            vals = self._dict_tree.item(item_id, "values")
            if not vals:
                self.toast("⚠️ 請點選具體詞彙進行刪除，不可整類刪除", is_error=True, duration=2500)
                return
            word = vals[0]
            if dictionary_manager.delete_word(word):
                self.toast(f"🗑️ 已刪除詞彙「{word}」", is_error=False, duration=2000)
                self._refresh_dictionary_list()
                
        tk.Button(
            add_box, text=" 🗑️ 刪除選取 ", command=do_delete_word,
            font=("Microsoft JhengHei", 9),
            bg="#c0392b", fg="white", bd=0, padx=8, pady=3
        ).pack(side="left", padx=(6, 0))
        
        # --- Bottom Toolbar: Import / Export / Notepad ---
        toolbar = tk.Frame(self.dictionary_win, bg=self.BG_DARK, padx=16, pady=10)
        toolbar.pack(fill="x")
        
        # 1. 匯入字典按鈕
        tk.Button(
            toolbar, text=" 📥 匯入字典 (Import)... ", command=self._prompt_import_dictionary,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#2980b9", fg="white", bd=0, padx=10, pady=5
        ).pack(side="left", padx=(0, 6))
        
        # 2. 匯出字典按鈕
        tk.Button(
            toolbar, text=" 📤 匯出字典 (Export)... ", command=self._prompt_export_dictionary,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#8e44ad", fg="white", bd=0, padx=10, pady=5
        ).pack(side="left", padx=6)
        
        # 3. 記事本開啟
        def open_notepad():
            import subprocess
            subprocess.Popen(['notepad.exe', dictionary_manager.get_dictionary_path()])
            
        tk.Button(
            toolbar, text=" 📝 記事本開啟 ", command=open_notepad,
            font=("Microsoft JhengHei", 9),
            bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=8, pady=5
        ).pack(side="right")
        
        # 綁定即時搜尋過濾
        self._dict_search_var.trace_add("write", lambda *args: self._filter_dictionary_list())
        self._refresh_dictionary_list()

    def _refresh_dictionary_list(self):
        import dictionary_manager
        if not hasattr(self, '_dict_tree') or not self._dict_tree:
            return
        self._all_categorized_words = dictionary_manager.load_categorized_words()
        total_words = sum(len(w) for w in self._all_categorized_words.values())
        total_cats = len(self._all_categorized_words)
        if hasattr(self, '_dict_count_lbl') and self._dict_count_lbl:
            self._dict_count_lbl.config(text=f"目前收錄 {total_words} 筆專用詞彙（共 {total_cats} 大分類，AI 優先參考修正）")
            
        if hasattr(self, '_dict_cat_menu') and self._dict_cat_menu:
            cat_list = list(self._all_categorized_words.keys())
            self._dict_cat_menu['values'] = cat_list
            if (not self._dict_cat_var.get() or self._dict_cat_var.get() not in cat_list) and cat_list:
                self._dict_cat_var.set("地理、數學與學術名詞" if "地理、數學與學術名詞" in cat_list else cat_list[0])
                
        self._filter_dictionary_list()

    def _filter_dictionary_list(self):
        if not hasattr(self, '_dict_tree') or not self._dict_tree:
            return
            
        # 記錄現有分類的展開狀態
        expanded_cats = set()
        for c in self._dict_tree.get_children():
            if self._dict_tree.item(c, "open"):
                expanded_cats.add(c)
                
        query = self._dict_search_var.get().strip().lower() if hasattr(self, '_dict_search_var') else ""
        self._dict_tree.delete(*self._dict_tree.get_children())
        all_cats = getattr(self, '_all_categorized_words', {})
        
        for cat_name, words in all_cats.items():
            matching_words = [w for w in words if not query or query in w.lower()]
            if query and not matching_words:
                continue
                
            cat_id = f"cat_{cat_name}"
            # 搜尋模式時自動展開匹配分類，一般模式預設收起 (若先前已展開則保持)
            should_open = bool(query) or (cat_id in expanded_cats)
            cat_text = f"📁 {cat_name} ({len(matching_words)})"
            self._dict_tree.insert("", "end", iid=cat_id, text=cat_text, open=should_open, tags=("category",))
            
            for w in matching_words:
                self._dict_tree.insert(cat_id, "end", iid=f"word_{cat_name}_{w}", text=f"  {w}", tags=("word",), values=(w, cat_name))

    def _prompt_import_dictionary(self):
        from tkinter import filedialog
        parent_win = self.dictionary_win if (self.dictionary_win and self.dictionary_win.winfo_exists()) else self.root
        
        filepath = filedialog.askopenfilename(
            parent=parent_win,
            title="選擇要匯入的專屬字典檔案",
            filetypes=[("文字檔案 (*.txt)", "*.txt"), ("所有檔案 (*.*)", "*.*")]
        )
        if not filepath:
            return
            
        self._show_import_mode_dialog(filepath)

    def _show_import_mode_dialog(self, filepath):
        import dictionary_manager
        parent_win = self.dictionary_win if (self.dictionary_win and self.dictionary_win.winfo_exists()) else self.root
        
        dialog = tk.Toplevel(parent_win)
        dialog.title("選擇字典匯入方式")
        dialog.configure(bg=self.BG_DARK)
        dialog.attributes("-topmost", True)
        dialog.transient(parent_win)
        dialog.grab_set()
        
        w, h = 440, 220
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        fname = os.path.basename(filepath)
        tk.Label(
            dialog, text=f"📥 準備匯入檔案：{fname}",
            font=("Microsoft JhengHei", 11, "bold"),
            fg=self.FG_TEXT, bg=self.BG_DARK
        ).pack(pady=(16, 6))
        
        tk.Label(
            dialog, 
            text="請選擇匯入模式：\n• 合併增補：保留既有詞彙，只追加新詞並自動去重複 (推薦)\n• 完全覆蓋：以匯入檔完全取代目前字典 (無法復原)",
            font=("Microsoft JhengHei", 9), justify="left",
            fg=self.FG_DIM, bg=self.BG_DARK
        ).pack(pady=4, padx=20)
        
        btn_box = tk.Frame(dialog, bg=self.BG_DARK)
        btn_box.pack(pady=14)
        
        def do_merge():
            dialog.destroy()
            try:
                added, total = dictionary_manager.import_dictionary(filepath, mode="merge")
                self.toast(f"✅ 字典合併完成！新增 {added} 筆新詞 (目前共 {total} 筆)", is_error=False, duration=3500)
                if hasattr(self, '_refresh_dictionary_list'):
                    self._refresh_dictionary_list()
            except Exception as e:
                self.toast(f"⚠️ 匯入失敗: {e}", is_error=True, duration=4000)
                
        def do_overwrite():
            dialog.destroy()
            try:
                count, total = dictionary_manager.import_dictionary(filepath, mode="overwrite")
                self.toast(f"🔄 字典已完全覆蓋！共匯入 {total} 筆詞彙", is_error=False, duration=3500)
                if hasattr(self, '_refresh_dictionary_list'):
                    self._refresh_dictionary_list()
            except Exception as e:
                self.toast(f"⚠️ 覆蓋失敗: {e}", is_error=True, duration=4000)
                
        tk.Button(
            btn_box, text=" ➕ 合併增補 (推薦) ", command=do_merge,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#27ae60", fg="white", bd=0, padx=10, pady=5
        ).pack(side="left", padx=6)
        
        tk.Button(
            btn_box, text=" ⚠️ 完全覆蓋 ", command=do_overwrite,
            font=("Microsoft JhengHei", 9),
            bg="#e67e22", fg="white", bd=0, padx=10, pady=5
        ).pack(side="left", padx=6)
        
        tk.Button(
            btn_box, text=" 取消 ", command=dialog.destroy,
            font=("Microsoft JhengHei", 9),
            bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=10, pady=5
        ).pack(side="left", padx=6)

    def _prompt_export_dictionary(self):
        import dictionary_manager
        from tkinter import filedialog
        from datetime import datetime
        parent_win = self.dictionary_win if (self.dictionary_win and self.dictionary_win.winfo_exists()) else self.root
        
        default_name = f"NoType_Dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(
            parent=parent_win,
            title="選擇匯出儲存位置",
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("文字檔案 (*.txt)", "*.txt"), ("所有檔案 (*.*)", "*.*")]
        )
        if not filepath:
            return
            
        try:
            count = dictionary_manager.export_dictionary(filepath)
            fname = os.path.basename(filepath)
            self.toast(f"✅ 專屬字典已成功匯出至：{fname} (共 {count} 筆詞彙)", is_error=False, duration=3500)
        except Exception as e:
            self.toast(f"⚠️ 匯出失敗: {e}", is_error=True, duration=4000)

    def process_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == 'show_toast':
                    _, text, bg, duration = item
                    self.show_toast(text, bg, duration)
                elif isinstance(item, tuple) and item[0] == 'open_quick_learn':
                    _, wrong_text, callback = item
                    self.open_quick_learn(wrong_text, callback)
                elif item == 'show_floating':
                    self.show_floating()
                elif item == 'hide_floating':
                    self.hide_floating()
                elif item == 'open_settings':
                    self.open_settings()
                elif item == 'open_help':
                    self.open_help()
                elif item == 'open_history':
                    self.open_history()
                elif item == 'open_dictionary':
                    self.open_dictionary()
                elif item == 'import_dictionary':
                    self._prompt_import_dictionary()
                elif item == 'export_dictionary':
                    self._prompt_export_dictionary()
                elif item == 'open_history':
                    self.open_history()
                elif item == 'refresh_history':
                    if self.history_win and self.history_win.winfo_exists():
                        self._refresh_history()
                elif item == 'quit':
                    self.root.quit()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
        
    def start(self):
        self.root.after(100, self.process_queue)
        self.root.mainloop()

# 建立全域單例供其他執行緒呼叫
ui = UIManager()
