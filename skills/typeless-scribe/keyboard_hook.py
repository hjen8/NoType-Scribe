import threading
from pynput import keyboard
import pyperclip
import time
from ui_manager import ui
from audio_logic import AudioRecorder
from groq_api import transcribe_audio, generate_notes, safe_print
from history_manager import HistoryRecord, add_record

# 將所有可能的 Alt 鍵名稱統一列出，確保相容性
ALT_KEYS = {keyboard.Key.alt_l, keyboard.Key.alt_r}
# 某些鍵盤佈局有 alt_gr，也納入保護
try:
    ALT_KEYS.add(keyboard.Key.alt)
except AttributeError:
    pass
try:
    ALT_KEYS.add(keyboard.Key.alt_gr)
except AttributeError:
    pass
def _is_right_alt(key):
    if key in {keyboard.Key.alt_r, getattr(keyboard.Key, 'alt_gr', None)}:
        return True
    if hasattr(key, 'vk') and key.vk == 165:
        return True
    return False

def _is_f8(key):
    return key == keyboard.Key.f8

def _is_f9(key):
    return key == keyboard.Key.f9

def _is_shift(key):
    return key in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}

class KeyboardManager:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.is_recording = False
        self.alt_r_pressed = False
        self.alt_r_down_time = 0.0
        self.f8_pressed = False
        self.f9_pressed = False
        self.shift_pressed = False
        self.listener = None
        self.target_hwnd = None
        self.app_context = None

    def _detect_app_context(self, hwnd) -> dict:
        import ctypes
        import os
        
        if not hwnd:
            return {"name": "general", "title": "", "mode": "general"}
            
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        title_buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        title = title_buf.value.lower()
        
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        proc_name = ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if h_proc:
            exe_buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            if kernel32.QueryFullProcessImageNameW(h_proc, 0, exe_buf, ctypes.byref(size)):
                proc_name = os.path.basename(exe_buf.value).lower()
            kernel32.CloseHandle(h_proc)
            
        chat_exes = {"line.exe", "discord.exe", "telegram.exe", "wechat.exe", "whatsapp.exe", "messenger.exe"}
        email_exes = {"outlook.exe", "thunderbird.exe", "mail.exe", "teams.exe", "slack.exe"}
        doc_exes = {"winword.exe", "powerpnt.exe", "excel.exe", "obsidian.exe", "notion.exe", "onenote.exe", "typora.exe", "notepad.exe"}
        code_exes = {"code.exe", "windowsterminal.exe", "powershell.exe", "cmd.exe", "pycharm64.exe", "devenv.exe", "antigravity.exe"}
        
        if proc_name in chat_exes or any(k in title for k in ["line", "discord", "wechat", "telegram"]):
            return {"name": proc_name or "chat", "title": title, "mode": "chat"}
        elif proc_name in email_exes or any(k in title for k in ["outlook", "gmail", "mail", "teams", "slack"]):
            return {"name": proc_name or "email", "title": title, "mode": "email"}
        elif proc_name in doc_exes or any(k in title for k in ["word", "powerpoint", "obsidian", "notion", "記事本"]):
            return {"name": proc_name or "doc", "title": title, "mode": "doc"}
        elif proc_name in code_exes or any(k in title for k in ["visual studio", "terminal", "command prompt", "powershell", "antigravity"]):
            return {"name": proc_name or "code", "title": title, "mode": "code"}
            
        return {"name": proc_name or "general", "title": title, "mode": "general"}

    def _get_selected_text(self):
        import pyautogui
        old_clip = ""
        try:
            old_clip = pyperclip.paste()
        except Exception:
            pass
            
        pyperclip.copy("")
        time.sleep(0.05)
        
        # 強制釋放可能被使用者手動按住的修飾鍵（特別是 Shift 鍵！否則在 Antigravity/Chrome/VSCode 中會觸發 Ctrl+Shift+C 開發者工具而非複製文字）
        for k in ['shift', 'shiftleft', 'shiftright', 'alt', 'altleft', 'altright']:
            try:
                pyautogui.keyUp(k)
            except Exception:
                pass
                
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.15)
        
        selected = ""
        try:
            selected = pyperclip.paste()
        except Exception:
            pass
            
        # 若第一次未取到（可能特定應用程式稍微卡頓），重試一次
        if not selected or not selected.strip():
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.12)
            try:
                selected = pyperclip.paste()
            except Exception:
                pass
            
        if not selected or not selected.strip():
            try:
                if old_clip:
                    pyperclip.copy(old_clip)
            except Exception:
                pass
            return None, None
            
        return selected.strip(), old_clip

    def _force_focus_and_paste(self, target_hwnd, text, wrong_text=None, old_clip=None):
        import ctypes
        import pyautogui
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        time.sleep(0.25)
        # 1. 精準將 Windows 焦點拉回使用者的編輯器視窗 (例如 Word、記事本)
        if target_hwnd:
            try:
                cur_th = kernel32.GetCurrentThreadId()
                tgt_th = user32.GetWindowThreadProcessId(target_hwnd, None)
                if cur_th != tgt_th:
                    user32.AttachThreadInput(cur_th, tgt_th, True)
                    user32.ShowWindow(target_hwnd, 5) # SW_SHOW
                    user32.SetForegroundWindow(target_hwnd)
                    user32.AttachThreadInput(cur_th, tgt_th, False)
                else:
                    user32.SetForegroundWindow(target_hwnd)
            except Exception as e:
                print(f"[Focus Warning] {e}")
                
        time.sleep(0.15)
        
        # 2. 強制釋放所有可能殘留的修飾鍵
        for k in ['shift', 'alt', 'altright', 'ctrl']:
            try:
                pyautogui.keyUp(k)
            except Exception:
                pass
                
        time.sleep(0.05)
        
        # 3. 智慧反白校正：檢查錯字是否依然處於反白狀態
        # 若 Word 將選取範圍瓦解、游標停在錯字後方，自動往左反向選取對應字數，100% 確保覆蓋替換！
        if wrong_text:
            pyperclip.copy("")
            time.sleep(0.02)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.08)
            current_selected = pyperclip.paste()
            
            if not current_selected:
                num_chars = len(wrong_text)
                for _ in range(num_chars):
                    pyautogui.hotkey('shift', 'left')
                    time.sleep(0.02)
                print(f"[Smart Replace] Re-selected {num_chars} chars backwards for '{wrong_text}'")
        
        # 4. 複製並貼上新文字
        pyperclip.copy(text)
        time.sleep(0.08)
        pyautogui.hotkey('ctrl', 'v')
        print(f"[Paste OK] Text '{text}' successfully replaced '{wrong_text}' in HWND {target_hwnd}")
        
        # 5. 留 1.5 秒緩衝再還原剪貼簿，確保 Word 徹底吃進文字
        if old_clip:
            time.sleep(1.5)
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass

    def _rephrase_selection_thread(self, selected_text, old_clip, target_hwnd):
        try:
            ui.toast("⏳ 正在重新修飾選取文字...", is_error=False, duration=2000)
            refined = generate_notes(selected_text)
            self._force_focus_and_paste(target_hwnd, refined, selected_text, old_clip)
            ui.toast("✅ 選取文字已重新修飾替換！", is_error=False, duration=2000)
        except Exception as e:
            print(f"[F8 Error] {e}")
            ui.toast(f"⚠️ 修飾失敗: {e}", is_error=True, duration=3000)

    def process_f8(self):
        import ctypes
        target_hwnd = ctypes.windll.user32.GetForegroundWindow()
        selected_text, old_clip = self._get_selected_text()
        if not selected_text:
            ui.toast("⚠️ 請先用滑鼠反白選取要處理的文字", is_error=True, duration=2500)
            return

        if self.shift_pressed:
            # Shift + F8: 極速教學與自適應學習浮窗
            def on_saved(correct_word):
                def paste_worker():
                    self._force_focus_and_paste(target_hwnd, correct_word, selected_text, old_clip)
                threading.Thread(target=paste_worker, daemon=True).start()
                        
            ui.msg_queue.put(('open_quick_learn', selected_text, on_saved))
        else:
            # 純 F8: 選取文字重新修飾
            threading.Thread(
                target=self._rephrase_selection_thread,
                args=(selected_text, old_clip, target_hwnd),
                daemon=True
            ).start()

    def process_audio_thread(self, file_path, duration_sec, app_context=None, target_hwnd=None):
        record = HistoryRecord(
            duration_sec=duration_sec,
            audio_path=file_path
        )
        try:
            print("\n[STT] Starting transcription...")
            start = time.time()
            transcript = transcribe_audio(file_path)
            print(f"[STT] Done ({time.time()-start:.1f}s): {transcript}")

            if not transcript or not transcript.strip():
                print("[STT] No valid speech detected.")
                record.status = "failed"
                record.error_msg = "未偵測到清晰語音"
                record.refined_text = "(未偵測到語音)"
                add_record(record)
                ui.msg_queue.put('refresh_history')
                ui.toast("未偵測到清晰語音，請重試", is_error=True, duration=2500)
                return
            
            record.raw_text = transcript.strip()
            
            app_mode = app_context.get('mode', 'general') if app_context else 'general'
            app_name = app_context.get('name', 'App') if app_context else 'App'
            print(f"[LLM] Starting refinement with App Mode: '{app_mode}' ({app_name})...")
            start = time.time()
            
            def notify_switch(msg):
                ui.toast(msg, is_error=False, duration=3500)
                
            try:
                refined_text = generate_notes(transcript, on_model_switch=notify_switch, app_mode=app_mode)
            except Exception as llm_err:
                safe_print(f"[LLM Fallback] ⚠️ LLM 服務異常 ({llm_err})，自動降級使用原始逐字稿並套用糾錯字典！")
                from learning_manager import apply_corrections
                from groq_api import apply_dictionary_post_process
                refined_text = apply_dictionary_post_process(apply_corrections(transcript.strip()))
                
            safe_print(f"[LLM] Done ({time.time()-start:.1f}s): {refined_text}")
            
            # 【物理層零空值熔斷保險 (Zero-Empty Fallback)】
            # 若 LLM 回傳空字串或僅含空白，強制自動降級使用原始逐字稿，徹底杜絕空字串存檔與貼空
            if not refined_text or not refined_text.strip():
                safe_print("[LLM Fallback] ⚠️ LLM 回傳空字串，自動降級使用原始逐字稿！")
                from learning_manager import apply_corrections
                from groq_api import apply_dictionary_post_process
                refined_text = apply_dictionary_post_process(apply_corrections(transcript.strip()))
            else:
                refined_text = refined_text.strip()
            
            record.status = "success"
            record.refined_text = refined_text
            add_record(record)
            ui.msg_queue.put('refresh_history')
            
            # 確保焦點鎖定在原本說話的視窗
            if target_hwnd:
                try:
                    import ctypes
                    cur_th = ctypes.windll.kernel32.GetCurrentThreadId()
                    tgt_th = ctypes.windll.user32.GetWindowThreadProcessId(target_hwnd, None)
                    if cur_th != tgt_th:
                        ctypes.windll.user32.AttachThreadInput(cur_th, tgt_th, True)
                        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
                        ctypes.windll.user32.AttachThreadInput(cur_th, tgt_th, False)
                    else:
                        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
                except Exception:
                    pass
                time.sleep(0.08)
            
            # 備份使用者原本的剪貼簿內容 (僅限文字)
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass
            
            # 替換為 AI 修飾後的文字
            pyperclip.copy(refined_text)
            time.sleep(0.1)  # 確保 Windows 剪貼簿已經準備好
            
            import pyautogui
            # 釋放修飾鍵防護
            for k in ['shift', 'alt', 'altright', 'ctrl']:
                try:
                    pyautogui.keyUp(k)
                except Exception:
                    pass
            # 模擬送出 Ctrl+V
            pyautogui.hotkey('ctrl', 'v')
            print(f"[OK] Text pasted to cursor! (Mode: {app_mode})")
            
            # 留緩衝時間讓 Windows 完成貼上動作，再還原原本的剪貼簿
            time.sleep(0.8)
            try:
                if original_clipboard:
                    pyperclip.copy(original_clipboard)
            except Exception:
                pass
            
        except Exception as e:
            err_msg = str(e)
            print(f"[ERROR] {err_msg}")
            record.status = "failed"
            record.error_msg = err_msg
            record.refined_text = f"({err_msg[:50]})"
            add_record(record)
            ui.msg_queue.put('refresh_history')
            
            if "NEED_KEY" in err_msg:
                clean_msg = err_msg.replace("NEED_KEY:", "").strip()
                ui.toast(f"🔑 {clean_msg}", is_error=True, duration=4500)
                ui.msg_queue.put('open_settings')
            elif "💡" in err_msg:
                ui.toast(err_msg, is_error=False, duration=4000)
            else:
                ui.toast(f"⚠️ {err_msg}", is_error=True, duration=4000)

    def _start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        import ctypes
        self.target_hwnd = ctypes.windll.user32.GetForegroundWindow()
        self.app_context = self._detect_app_context(self.target_hwnd)
        print(f"\n[REC] Recording started... (Active App: {self.app_context['name']} | Mode: {self.app_context['mode']})")
        ui.msg_queue.put('show_floating')
        self.recorder.start_recording()

    def _stop_recording_and_process(self, trigger_type="Toggle"):
        if not self.is_recording:
            return
        self.is_recording = False
        print(f"[REC] Recording stopped ({trigger_type}), processing...")
        ui.msg_queue.put('hide_floating')
        file_path, duration_sec = self.recorder.stop_recording()
        
        if file_path:
            threading.Thread(
                target=self.process_audio_thread,
                args=(file_path, duration_sec, self.app_context, self.target_hwnd),
                daemon=True
            ).start()

    def _win32_filter(self, msg, data):
        # 165 is VK_RMENU (Right Alt)
        if data.vkCode == 165:
            if msg in (0x100, 0x104):  # WM_KEYDOWN / WM_SYSKEYDOWN
                if not self.alt_r_pressed:
                    self.alt_r_pressed = True
                    self.alt_r_down_time = time.time()
                    if not self.is_recording:
                        self._start_recording()
                    else:
                        self._stop_recording_and_process(trigger_type="Toggle Click (Right Alt)")
            elif msg in (0x101, 0x105):  # WM_KEYUP / WM_SYSKEYUP
                down_time = getattr(self, 'alt_r_down_time', 0.0)
                self.alt_r_pressed = False
                if self.is_recording and down_time > 0:
                    held_duration = time.time() - down_time
                    if held_duration >= 0.6:
                        self._stop_recording_and_process(trigger_type=f"Hold-to-Talk (Right Alt) {held_duration:.1f}s")
            # 物理吞噬此事件，向 Windows 回傳 1，徹底杜絕 SC_KEYMENU 系統選單奪焦
            if self.listener:
                self.listener.suppress_event()
            return False
        return True

    def on_press(self, key):
        try:
            if _is_shift(key):
                self.shift_pressed = True

            if _is_f8(key):
                if not self.f8_pressed:
                    self.f8_pressed = True
                    self.process_f8()

            elif _is_f9(key):
                if not self.f9_pressed:
                    self.f9_pressed = True
                    if not self.is_recording:
                        self._start_recording()
                    else:
                        self._stop_recording_and_process(trigger_type="Toggle Click (F9)")

            elif _is_right_alt(key):
                # 若非 Windows 底層攔截環境之備援
                if not self.alt_r_pressed:
                    self.alt_r_pressed = True
                    self.alt_r_down_time = time.time()
                    if not self.is_recording:
                        self._start_recording()
                    else:
                        self._stop_recording_and_process(trigger_type="Toggle Click (Right Alt)")
        except Exception as e:
            print(f"[ERROR] on_press: {e}")

    def on_release(self, key):
        try:
            if _is_shift(key):
                self.shift_pressed = False
            if _is_f8(key):
                self.f8_pressed = False
            if _is_f9(key):
                self.f9_pressed = False
            if _is_right_alt(key):
                down_time = getattr(self, 'alt_r_down_time', 0.0)
                self.alt_r_pressed = False
                if self.is_recording and down_time > 0:
                    held_duration = time.time() - down_time
                    if held_duration >= 0.6:
                        self._stop_recording_and_process(trigger_type=f"Hold-to-Talk (Right Alt) {held_duration:.1f}s")
        except Exception as e:
            print(f"[ERROR] on_release: {e}")

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
            win32_event_filter=self._win32_filter
        )
        self.listener.start()
        print("[Keyboard] Hotkey listener started:")
        print("  <右側 Alt>   : 語音輸入主熱鍵 (支援單擊切換 / 長按放開雙模態，底層防失焦阻截)")
        print("  <F9>         : 備用語音輸入 (單擊切換錄音與貼上)")
        print("  <F8>         : 桌面反白文字重新修飾")
        print("  <Shift + F8> : 桌面反白文字極速糾錯教學與自適應學習")
