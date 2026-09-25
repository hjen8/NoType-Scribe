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
        self.student_reminder_win = None
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
        
        win_w, win_h = 500, 415
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
        wrong_var = tk.StringVar(value=wrong_text if wrong_text else "")
        entry_wrong = tk.Entry(row1, textvariable=wrong_var, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_wrong.pack(side="left", fill="x", expand=True)
            
        # 正確的詞
        row2 = tk.Frame(dialog, bg=self.BG_DARK)
        row2.pack(fill="x", padx=20, pady=3)
        tk.Label(row2, text="正確的詞：", font=("Microsoft JhengHei", 9, "bold"), fg="#f39c12", bg=self.BG_DARK, width=10, anchor="w").pack(side="left")
        correct_var = tk.StringVar(value=wrong_text if wrong_text else "")
        entry_correct = tk.Entry(row2, textvariable=correct_var, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_correct.pack(side="left", fill="x", expand=True)
        entry_correct.focus_set()
        if wrong_text:
            entry_correct.icursor(tk.END)
            dialog.after(50, lambda: (entry_correct.focus_set(), entry_correct.icursor(tk.END)))
        entry_correct.bind("<Control-a>", lambda e: (entry_correct.select_range(0, tk.END), "break")[1])
        entry_wrong.bind("<Control-a>", lambda e: (entry_wrong.select_range(0, tk.END), "break")[1])

        # 自動歸類分類選單
        import dictionary_manager
        from learning_manager import check_homophone_ambiguity
        cat_options = dictionary_manager.get_categories()
        default_pred = dictionary_manager.predict_category(wrong_text)
        cat_var = tk.StringVar(value=default_pred if default_pred in cat_options else (cat_options[0] if cat_options else ""))
        
        row_cat = tk.Frame(dialog, bg=self.BG_DARK)
        row_cat.pack(fill="x", padx=20, pady=3)
        tk.Label(row_cat, text="自動歸類：", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK, width=10, anchor="w").pack(side="left")
        from tkinter import ttk
        cat_combo = ttk.Combobox(row_cat, textvariable=cat_var, values=cat_options, state="readonly", font=("Microsoft JhengHei", 9))
        cat_combo.pack(side="left", fill="x", expand=True)

        # 語境限制 (可選，以逗號分隔關鍵詞，如：考卷, 考試)
        row_ctx = tk.Frame(dialog, bg=self.BG_DARK)
        row_ctx.pack(fill="x", padx=20, pady=3)
        tk.Label(row_ctx, text="語境限制：", font=("Microsoft JhengHei", 9), fg="#3498db", bg=self.BG_DARK, width=10, anchor="w").pack(side="left")
        context_var = tk.StringVar(value="")
        entry_context = tk.Entry(row_ctx, textvariable=context_var, font=("Microsoft JhengHei", 9), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
        entry_context.pack(side="left", fill="x", expand=True)
        entry_context.bind("<Control-a>", lambda e: (entry_context.select_range(0, tk.END), "break")[1])
        
        # 提示標籤
        hint_text = "💡「僅本次替換」只修改當前選取文字；「永久學習」會自動歸類存入字典供日後自動校正"
        lbl_hint = tk.Label(
            dialog, 
            text=hint_text, 
            font=("Microsoft JhengHei", 8),
            fg="#95a5a6", bg=self.BG_DARK,
            justify="left", anchor="w"
        )
        lbl_hint.pack(anchor="w", padx=20, pady=(6, 8), fill="x")

        is_updating_warning = False
        def update_ambiguity_warning(*args):
            nonlocal is_updating_warning
            if is_updating_warning:
                return
            is_updating_warning = True
            try:
                w = wrong_var.get().strip()
                c = correct_var.get().strip()
                amb = check_homophone_ambiguity(w, c)
                current_ctx = context_var.get().strip()
                
                if amb.get("is_ambiguous"):
                    # 若使用者尚未手動修改語境，且系統有推薦關鍵詞，自動預填推薦語境
                    if not current_ctx and amb.get("suggested_context"):
                        context_var.set(amb["suggested_context"])
                        current_ctx = amb["suggested_context"]
                    
                    if current_ctx:
                        lbl_hint.config(
                            text=f"✅ 已設定語境限制（{current_ctx}）！\n僅在包含上述關鍵詞時替換，絕不誤傷其他前後用語。",
                            fg="#2ecc71",
                            font=("Microsoft JhengHei", 8, "bold")
                        )
                    else:
                        lbl_hint.config(
                            text=amb["warning"],
                            fg="#f39c12",
                            font=("Microsoft JhengHei", 8, "bold")
                        )
                else:
                    if current_ctx:
                        lbl_hint.config(
                            text=f"💡 已設定語境限制（{current_ctx}）。僅在命中關鍵詞時執行替換。",
                            fg="#3498db",
                            font=("Microsoft JhengHei", 8)
                        )
                    else:
                        lbl_hint.config(
                            text="💡「僅本次替換」只修改當前選取文字；「永久學習」會自動歸類存入字典供日後自動校正",
                            fg="#95a5a6",
                            font=("Microsoft JhengHei", 8)
                        )
            finally:
                is_updating_warning = False

        def on_correct_change(*args):
            txt = correct_var.get().strip()
            if txt:
                pred = dictionary_manager.predict_category(txt)
                if pred in cat_options:
                    cat_var.set(pred)
            update_ambiguity_warning()

        correct_var.trace_add("write", on_correct_change)
        wrong_var.trace_add("write", update_ambiguity_warning)
        context_var.trace_add("write", update_ambiguity_warning)
        update_ambiguity_warning()
        
        # 動作 1：僅本次替換 (不存入字典)
        def replace_once(event=None):
            correct = correct_var.get().strip()
            dialog.destroy()
            if correct:
                self.toast(f"✅ 已替換文字為「{correct}」（未存入字典）！", is_error=False, duration=2000)
                if on_saved:
                    on_saved(correct)
                    
        # 動作 2：永久學習並替換
        def replace_and_learn(event=None):
            wrong = wrong_var.get().strip()
            correct = correct_var.get().strip()
            chosen_cat = cat_var.get().strip()
            raw_ctx = context_var.get().strip()
            import re
            ctx_list = [c.strip() for c in re.split(r'[,，、\s]+', raw_ctx) if c.strip()] if raw_ctx else []
            
            if not correct:
                return

            # 多義詞防呆二次攔截（若已有明確語境限制，則屬於安全條件學習，免除高風險彈窗）
            amb = check_homophone_ambiguity(wrong, correct)
            if amb.get("is_ambiguous") and not ctx_list:
                from tkinter import messagebox
                confirm = messagebox.askyesno(
                    "⚠️ 永久學習高風險警示",
                    amb["popup_msg"],
                    parent=dialog
                )
                if not confirm:
                    # 使用者選擇否，取消永久學習，不關閉視窗，焦點切換至「僅本次替換」
                    btn_replace_once.focus_set()
                    return
            
            dialog.destroy()
            from learning_manager import add_correction
            add_correction(wrong, correct, category=chosen_cat, contexts=ctx_list)
            if ctx_list:
                self.toast(f"✅ 已存入條件糾錯（語境：{','.join(ctx_list[:3])}）：「{correct}」！", is_error=False, duration=2500)
            else:
                self.toast(f"✅ 已替換並存入【{chosen_cat}】：「{correct}」！", is_error=False, duration=2500)
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
        btn_replace_once = tk.Button(
            btn_box, text=" 僅本次替換 (Enter) ", command=replace_once,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#2980b9", fg="white", bd=0, padx=10, pady=4
        )
        btn_replace_once.pack(side="left", padx=6)
        
        # 2. 永久學習並替換
        btn_replace_learn = tk.Button(
            btn_box, text=" 永久學習並替換 (Shift+Enter) ", command=replace_and_learn,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#27ae60", fg="white", bd=0, padx=10, pady=4
        )
        btn_replace_learn.pack(side="left", padx=6)
        
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
    def open_dictionary(self, focus_category=None):
        import dictionary_manager
        
        if self.dictionary_win and self.dictionary_win.winfo_exists():
            self.dictionary_win.lift()
            self.dictionary_win.focus_force()
            self._refresh_dictionary_list()
            if focus_category:
                self._focus_dictionary_category(focus_category)
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
                def _open_rec(parent=""):
                    for c in self._dict_tree.get_children(parent):
                        self._dict_tree.item(c, open=True)
                        _open_rec(c)
                _open_rec("")
                    
        def collapse_all():
            if hasattr(self, '_dict_tree'):
                def _close_rec(parent=""):
                    for c in self._dict_tree.get_children(parent):
                        self._dict_tree.item(c, open=False)
                        _close_rec(c)
                _close_rec("")
                    
        tk.Button(
            search_box, text=" ➕ 展開全部 ", command=expand_all,
            font=("Microsoft JhengHei", 8), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=6, pady=2
        ).pack(side="left", padx=2)
        tk.Button(
            search_box, text=" ➖ 全部收起 ", command=collapse_all,
            font=("Microsoft JhengHei", 8), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=6, pady=2
        ).pack(side="left", padx=2)
        
        # 智慧雙模態上下移動（分類 或 詞彙）
        def move_selected_item(direction):
            sel = self._dict_tree.selection()
            if not sel:
                self.toast("⚠️ 請先在列表中點選欲調整順序的分類或詞彙", is_error=True, duration=2000)
                return
            item_id = sel[0]
            tags = self._dict_tree.item(item_id, "tags")
            import dictionary_manager
            action_text = "上移" if direction == "up" else "下移"
            
            if "category_l1" in tags:
                cat_ident = item_id.replace("cat_l1_", "")
                if dictionary_manager.move_category(cat_ident, direction):
                    self.toast(f"✅ 已{action_text}分類【{cat_ident}】！", is_error=False, duration=1500)
                    self._refresh_dictionary_list()
                    if self._dict_tree.exists(item_id):
                        self._dict_tree.selection_set(item_id)
                        self._dict_tree.see(item_id)
                else:
                    self.toast("⚠️ 已達該層級頂部或底部，無法再移動", is_error=True, duration=1500)
            elif "category_l2" in tags:
                cat_ident = item_id.replace("cat_l2_", "")
                if dictionary_manager.move_category(cat_ident, direction):
                    sub_name = cat_ident.split(" / ")[-1]
                    self.toast(f"✅ 已{action_text}子分類【{sub_name}】！", is_error=False, duration=1500)
                    self._refresh_dictionary_list()
                    if self._dict_tree.exists(item_id):
                        self._dict_tree.selection_set(item_id)
                        self._dict_tree.see(item_id)
                else:
                    self.toast("⚠️ 已達該層級頂部或底部，無法再移動", is_error=True, duration=1500)
            elif "word" in tags:
                vals = self._dict_tree.item(item_id, "values")
                if vals and len(vals) >= 2:
                    word = vals[0]
                    cat_path = vals[1]
                    if dictionary_manager.move_word(word, cat_path, direction):
                        self.toast(f"✅ 已{action_text}詞彙「{word}」！", is_error=False, duration=1500)
                        self._refresh_dictionary_list()
                        if self._dict_tree.exists(item_id):
                            self._dict_tree.selection_set(item_id)
                            self._dict_tree.see(item_id)
                    else:
                        self.toast("⚠️ 詞彙已達該分類頂部或底部，無法再移動", is_error=True, duration=1500)
            else:
                self.toast("⚠️ 請選取分類節點或詞彙項目進行移動", is_error=True, duration=2000)
                
        tk.Button(
            search_box, text=" ⬆️ 上移 ", command=lambda: move_selected_item("up"),
            font=("Microsoft JhengHei", 8), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=6, pady=2
        ).pack(side="left", padx=(10, 2))
        tk.Button(
            search_box, text=" ⬇️ 下移 ", command=lambda: move_selected_item("down"),
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
        
        self._dict_tree.tag_configure("category_l1", font=("Microsoft JhengHei", 10, "bold"), foreground="#f1c40f")
        self._dict_tree.tag_configure("category_l2", font=("Microsoft JhengHei", 9, "bold"), foreground="#3498db")
        self._dict_tree.tag_configure("word", font=("Microsoft JhengHei", 9), foreground="#ecf0f1")
        
        # 單擊展開/收起樹狀目錄 (點一下展開，再點一下收起)
        def on_tree_click(event):
            item_id = self._dict_tree.identify_row(event.y)
            if not item_id:
                return
            tags = self._dict_tree.item(item_id, "tags")
            # 若為分類節點 (大類或子類)
            if "category_l1" in tags or "category_l2" in tags:
                element = self._dict_tree.identify_element(event.x, event.y)
                # 排除原生小箭頭 (原生小箭頭已被 Tkinter 自動切換)
                if element != "Treeitem.indicator":
                    is_open = self._dict_tree.item(item_id, "open")
                    self._dict_tree.item(item_id, open=not is_open)
                
                # 自動連動底部新增分類選單
                if "category_l1" in tags:
                    cat_name = item_id.replace("cat_l1_", "")
                    if hasattr(self, '_dict_cat_menu') and self._dict_cat_menu:
                        options = self._dict_cat_menu['values']
                        matching = [opt for opt in options if opt == cat_name or opt.startswith(f"{cat_name} / ")]
                        if matching and hasattr(self, '_dict_cat_var'):
                            self._dict_cat_var.set(matching[0])
                elif "category_l2" in tags:
                    cat_path = item_id.replace("cat_l2_", "")
                    if hasattr(self, '_dict_cat_var'):
                        self._dict_cat_var.set(cat_path)
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
        
        self._dict_cat_var = tk.StringVar(value="地理 / 氣候水文與大氣")
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
            cat = self._dict_cat_var.get().strip() if hasattr(self, '_dict_cat_var') else "地理 / 氣候水文與大氣"
            if val:
                if dictionary_manager.add_word(val, category=cat):
                    self.toast(f"✅ 已新增「{val}」至【{cat}】！", is_error=False, duration=2000)
                    self._dict_add_var.set("")
                    self._refresh_dictionary_list()
                    if " / " in cat:
                        p, s = cat.split(" / ", 1)
                        cat_l1_id = f"cat_l1_{p}"
                        if self._dict_tree.exists(cat_l1_id):
                            self._dict_tree.item(cat_l1_id, open=True)
                        sub_id = f"cat_l2_{cat}"
                        if self._dict_tree.exists(sub_id):
                            self._dict_tree.item(sub_id, open=True)
                            word_id = f"word_{p}_{s}_{val}"
                            if self._dict_tree.exists(word_id):
                                self._dict_tree.selection_set(word_id)
                                self._dict_tree.see(word_id)
                    else:
                        cat_id = f"cat_l1_{cat}"
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
        ).pack(side="left", padx=(0, 4))
        
        # 修改選取詞彙對話框
        def do_edit_word(target_item_id=None):
            sel = [target_item_id] if target_item_id else self._dict_tree.selection()
            if not sel:
                self.toast("⚠️ 請先在列表中點選要修改的詞彙", is_error=True, duration=2000)
                return
            item_id = sel[0]
            vals = self._dict_tree.item(item_id, "values")
            if not vals:
                self.toast("⚠️ 只能編輯具體詞彙，不可編輯分類標題", is_error=True, duration=2000)
                return
            old_word = vals[0]
            old_cat = vals[1]
            
            edit_win = tk.Toplevel(self.dictionary_win if self.dictionary_win else self.root)
            edit_win.title("修改專屬詞彙")
            edit_win.configure(bg=self.BG_DARK)
            edit_win.attributes("-topmost", True)
            w, h = 420, 200
            sw = edit_win.winfo_screenwidth()
            sh = edit_win.winfo_screenheight()
            edit_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
            edit_win.resizable(False, False)
            
            tk.Label(
                edit_win, text=f"✏️ 修改詞彙：{old_word}",
                font=("Microsoft JhengHei", 11, "bold"),
                fg=self.FG_TEXT, bg=self.BG_DARK
            ).pack(anchor="w", padx=20, pady=(15, 8))
            
            f1 = tk.Frame(edit_win, bg=self.BG_DARK)
            f1.pack(fill="x", padx=20, pady=4)
            tk.Label(f1, text="新詞彙名稱：", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK, width=11, anchor="w").pack(side="left")
            entry_new = tk.Entry(f1, font=("Microsoft JhengHei", 10), bg=self.BG_CARD, fg="white", insertbackground="white", bd=1)
            entry_new.pack(side="left", fill="x", expand=True)
            entry_new.insert(0, old_word)
            entry_new.focus_set()
            entry_new.select_range(0, tk.END)
            
            f2 = tk.Frame(edit_win, bg=self.BG_DARK)
            f2.pack(fill="x", padx=20, pady=4)
            tk.Label(f2, text="所屬分類：", font=("Microsoft JhengHei", 9), fg=self.FG_DIM, bg=self.BG_DARK, width=11, anchor="w").pack(side="left")
            import dictionary_manager
            all_cats = dictionary_manager.get_categories()
            edit_cat_var = tk.StringVar(value=old_cat if old_cat in all_cats else (all_cats[0] if all_cats else ""))
            combo_cat = ttk.Combobox(f2, textvariable=edit_cat_var, values=all_cats, state="readonly", font=("Microsoft JhengHei", 9))
            combo_cat.pack(side="left", fill="x", expand=True)
            
            def save_edit(event=None):
                new_w = entry_new.get().strip()
                new_c = edit_cat_var.get().strip()
                if not new_w:
                    self.toast("⚠️ 詞彙名稱不能為空", is_error=True, duration=2000)
                    return
                edit_win.destroy()
                if dictionary_manager.edit_word(old_word, new_w, new_c):
                    self.toast(f"✅ 已更新詞彙為「{new_w}」！", is_error=False, duration=2000)
                    self._refresh_dictionary_list()
                    if " / " in new_c:
                        p, s = new_c.split(" / ", 1)
                        if self._dict_tree.exists(f"cat_l1_{p}"):
                            self._dict_tree.item(f"cat_l1_{p}", open=True)
                        sub_id = f"cat_l2_{new_c}"
                        if self._dict_tree.exists(sub_id):
                            self._dict_tree.item(sub_id, open=True)
                            wid = f"word_{p}_{s}_{new_w}"
                            if self._dict_tree.exists(wid):
                                self._dict_tree.selection_set(wid)
                                self._dict_tree.see(wid)
                    else:
                        cid = f"cat_l1_{new_c}"
                        if self._dict_tree.exists(cid):
                            self._dict_tree.item(cid, open=True)
                            wid = f"word_{new_c}_{new_w}"
                            if self._dict_tree.exists(wid):
                                self._dict_tree.selection_set(wid)
                                self._dict_tree.see(wid)
                else:
                    self.toast("⚠️ 修改失敗，請確認詞彙有效性", is_error=True, duration=2000)
                    
            entry_new.bind("<Return>", save_edit)
            edit_win.bind("<Escape>", lambda e: edit_win.destroy())
            
            btn_row = tk.Frame(edit_win, bg=self.BG_DARK)
            btn_row.pack(pady=(12, 10))
            tk.Button(
                btn_row, text=" 💾 儲存修改 (Enter) ", command=save_edit,
                font=("Microsoft JhengHei", 9, "bold"), bg="#2980b9", fg="white", bd=0, padx=12, pady=4
            ).pack(side="left", padx=6)
            tk.Button(
                btn_row, text=" 取消 (Esc) ", command=edit_win.destroy,
                font=("Microsoft JhengHei", 9), bg=self.BTN_BG, fg=self.FG_TEXT, bd=0, padx=10, pady=4
            ).pack(side="left", padx=6)
            
        tk.Button(
            add_box, text=" ✏️ 修改選取 ", command=do_edit_word,
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#2980b9", fg="white", bd=0, padx=8, pady=3
        ).pack(side="left", padx=(0, 4))
        
        # 雙擊詞彙直接喚起修改
        def on_tree_double_click(event):
            item_id = self._dict_tree.identify_row(event.y)
            if not item_id:
                return
            tags = self._dict_tree.item(item_id, "tags")
            if "word" in tags:
                do_edit_word(target_item_id=item_id)
        self._dict_tree.bind("<Double-Button-1>", on_tree_double_click)
        
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
        
        # 3. 7 月學生名單檢核按鈕
        tk.Button(
            toolbar, text=" 🎓 7 月學生名單檢核 ", command=lambda: self.show_student_reminder_dialog(force=True),
            font=("Microsoft JhengHei", 9, "bold"),
            bg="#d35400", fg="white", bd=0, padx=10, pady=5, cursor="hand2"
        ).pack(side="left", padx=6)
        
        # 4. 記事本開啟
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
        if focus_category:
            self._focus_dictionary_category(focus_category)

    def _focus_dictionary_category(self, category_name):
        if not hasattr(self, '_dict_tree') or not self._dict_tree:
            return
        cat_id = f"cat_l1_{category_name}"
        if self._dict_tree.exists(cat_id):
            self._dict_tree.item(cat_id, open=True)
            self._dict_tree.selection_set(cat_id)
            self._dict_tree.see(cat_id)
            self._dict_tree.focus(cat_id)
        if hasattr(self, '_dict_cat_var') and hasattr(self, '_dict_cat_menu') and self._dict_cat_menu:
            try:
                cat_list = self._dict_cat_menu.cget('values')
                if category_name in cat_list:
                    self._dict_cat_var.set(category_name)
            except Exception:
                pass

    def _refresh_dictionary_list(self):
        import dictionary_manager
        if not hasattr(self, '_dict_tree') or not self._dict_tree:
            return
        self._hierarchy = dictionary_manager.load_hierarchy()
        total_words = len(dictionary_manager.load_words())
        total_cats = len(self._hierarchy)
        if hasattr(self, '_dict_count_lbl') and self._dict_count_lbl:
            self._dict_count_lbl.config(text=f"目前收錄 {total_words} 筆專用詞彙（共 {total_cats} 大分類，AI 優先參考修正）")
            
        if hasattr(self, '_dict_cat_menu') and self._dict_cat_menu:
            cat_list = dictionary_manager.get_categories()
            self._dict_cat_menu['values'] = cat_list
            if (not self._dict_cat_var.get() or self._dict_cat_var.get() not in cat_list) and cat_list:
                pref = "地理 / 氣候水文與大氣"
                self._dict_cat_var.set(pref if pref in cat_list else cat_list[0])
                
        self._filter_dictionary_list()

    def _filter_dictionary_list(self):
        if not hasattr(self, '_dict_tree') or not self._dict_tree:
            return
            
        # 記錄現有分類的展開狀態 (遞迴蒐集)
        expanded_cats = set()
        def _collect_expanded(parent=""):
            for c in self._dict_tree.get_children(parent):
                if self._dict_tree.item(c, "open"):
                    expanded_cats.add(c)
                _collect_expanded(c)
        _collect_expanded("")
                
        query = self._dict_search_var.get().strip().lower() if hasattr(self, '_dict_search_var') else ""
        self._dict_tree.delete(*self._dict_tree.get_children())
        hierarchy = getattr(self, '_hierarchy', [])
        
        for cat in hierarchy:
            cat_name = cat.get("name", "")
            subs = cat.get("subcategories", [])
            cat_words = cat.get("words", [])
            
            # 若有子分類 (二層樹狀結構)
            if subs:
                sub_matches = []
                for sub in subs:
                    sub_name = sub.get("name", "")
                    matching_w = [w for w in sub.get("words", []) if not query or query in w.lower()]
                    if not query or matching_w or query in sub_name.lower():
                        sub_matches.append((sub_name, matching_w))
                        
                if query and not sub_matches and query not in cat_name.lower():
                    continue
                    
                total_cat_words = sum(len(w_list) for _, w_list in sub_matches)
                cat_id = f"cat_l1_{cat_name}"
                should_open_cat = bool(query) or (cat_id in expanded_cats)
                self._dict_tree.insert(
                    "", "end", iid=cat_id, 
                    text=f"📁 {cat_name} ({total_cat_words})", 
                    open=should_open_cat, 
                    tags=("category_l1",)
                )
                
                for sub_name, matching_w in sub_matches:
                    sub_id = f"cat_l2_{cat_name} / {sub_name}"
                    should_open_sub = bool(query) or (sub_id in expanded_cats)
                    self._dict_tree.insert(
                        cat_id, "end", iid=sub_id,
                        text=f"📂 {sub_name} ({len(matching_w)})",
                        open=should_open_sub,
                        tags=("category_l2",)
                    )
                    for w in matching_w:
                        self._dict_tree.insert(
                            sub_id, "end", iid=f"word_{cat_name}_{sub_name}_{w}",
                            text=f"  {w}",
                            tags=("word",),
                            values=(w, f"{cat_name} / {sub_name}")
                        )
            else:
                # 單層分類
                matching_words = [w for w in cat_words if not query or query in w.lower()]
                if query and not matching_words and query not in cat_name.lower():
                    continue
                cat_id = f"cat_l1_{cat_name}"
                should_open = bool(query) or (cat_id in expanded_cats)
                self._dict_tree.insert(
                    "", "end", iid=cat_id,
                    text=f"📁 {cat_name} ({len(matching_words)})",
                    open=should_open,
                    tags=("category_l1",)
                )
                for w in matching_words:
                    self._dict_tree.insert(
                        cat_id, "end", iid=f"word_{cat_name}_{w}",
                        text=f"  {w}",
                        tags=("word",),
                        values=(w, cat_name)
                    )

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

    def show_student_reminder_dialog(self, force=False):
        import config_manager
        print(f"[UI] 觸發 7 月學生名單例行檢核 (force={force})", flush=True)
        if not force and not config_manager.should_prompt_student_reminder():
            return
            
        if hasattr(self, 'student_reminder_win') and self.student_reminder_win and self.student_reminder_win.winfo_exists():
            try:
                self.student_reminder_win.deiconify()
                self.student_reminder_win.lift()
                self.student_reminder_win.focus_force()
            except Exception:
                pass
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("NoType 7 月新學年度學生名單例行檢核")
        dialog.configure(bg=self.BG_DARK)
        dialog.attributes("-topmost", True)
        self.student_reminder_win = dialog
        
        w, h = 560, 360
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        dialog.resizable(False, False)
        
        def on_close():
            # 關閉視窗預設設為 7 天後再提醒
            config_manager.set_student_reminder_snooze(7)
            dialog.destroy()
            self.student_reminder_win = None
            
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # --- 頂部圖示與標題 ---
        header = tk.Frame(dialog, bg=self.BG_DARK, padx=20, pady=16)
        header.pack(fill="x")
        
        tk.Label(
            header, text="🎓 7 月新學年度學生名單例行檢核",
            font=("Microsoft JhengHei", 14, "bold"),
            fg="#f39c12", bg=self.BG_DARK
        ).pack(anchor="w")
        
        desc_text = (
            "長官您好！現在是 7 月暑假與新學年度交接期，\n"
            "考量舊生畢業離班與新生入學，是否需要檢視或更新專屬字典中的【學生人名】清單？\n\n"
            "★ 更新【學生人名】可確保新學年度語音輸入 100% 精準命中新生姓名，\n"
            "享有最高優先先發優勢與同音防錯保險！（同事與親友人名不受影響）"
        )
        
        body = tk.Frame(dialog, bg=self.BG_DARK, padx=20)
        body.pack(fill="both", expand=True)
        
        tk.Label(
            body, text=desc_text,
            font=("Microsoft JhengHei", 10),
            fg=self.FG_TEXT, bg=self.BG_DARK,
            justify="left", wraplength=520
        ).pack(anchor="w", pady=(0, 15))
        
        # --- 操作選項按鈕區 ---
        btn_frame = tk.Frame(dialog, bg=self.BG_DARK, padx=20, pady=15)
        btn_frame.pack(fill="x")
        
        def action_open_dict():
            config_manager.set_student_reminder_done()
            dialog.destroy()
            self.student_reminder_win = None
            self.open_dictionary(focus_category="學生人名")
            self.toast("📚 已開啟字典並自動為您聚焦【學生人名】分類！", is_error=False, duration=3500)
            
        def action_snooze():
            config_manager.set_student_reminder_snooze(7)
            dialog.destroy()
            self.student_reminder_win = None
            self.toast("⏳ 已設定 7 天後再次溫和提醒！", is_error=False, duration=2500)
            
        def action_dismiss():
            config_manager.set_student_reminder_done()
            dialog.destroy()
            self.student_reminder_win = None
            self.toast("✅ 已確認完成！今年 7 月不再跳窗提醒。", is_error=False, duration=3000)
            
        btn_open = tk.Button(
            btn_frame, text=" 📚 立即開啟字典 (自動聚焦學生人名) ",
            command=action_open_dict,
            font=("Microsoft JhengHei", 10, "bold"),
            bg="#2980b9", fg="white", activebackground="#3498db", activeforeground="white",
            bd=0, padx=12, pady=8, cursor="hand2"
        )
        btn_open.pack(fill="x", pady=3)
        
        row_opts = tk.Frame(btn_frame, bg=self.BG_DARK)
        row_opts.pack(fill="x", pady=(6, 0))
        
        btn_snooze = tk.Button(
            row_opts, text=" ⏳ 7 天後再提醒 ",
            command=action_snooze,
            font=("Microsoft JhengHei", 9),
            bg="#d35400", fg="white", activebackground="#e67e22", activeforeground="white",
            bd=0, padx=8, pady=5, cursor="hand2"
        )
        btn_snooze.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        btn_done = tk.Button(
            row_opts, text=" ✅ 今年名單已確認 (今年不再提醒) ",
            command=action_dismiss,
            font=("Microsoft JhengHei", 9),
            bg="#27ae60", fg="white", activebackground="#2ecc71", activeforeground="white",
            bd=0, padx=8, pady=5, cursor="hand2"
        )
        btn_done.pack(side="right", fill="x", expand=True, padx=(4, 0))
        
        dialog.lift()
        dialog.focus_force()

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
                elif isinstance(item, tuple) and item[0] == 'open_dictionary':
                    _, cat = item
                    self.open_dictionary(focus_category=cat)
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
                elif item == 'check_student_reminder':
                    self.show_student_reminder_dialog(force=False)
                elif item == 'open_student_reminder':
                    try:
                        self.show_student_reminder_dialog(force=True)
                    except Exception as e:
                        print(f"[UI] Error opening student reminder dialog: {e}", flush=True)
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
