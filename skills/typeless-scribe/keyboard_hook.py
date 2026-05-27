import threading
from pynput import keyboard
import pyperclip
import time
from ui_manager import ui
from audio_logic import AudioRecorder
from groq_api import transcribe_audio, generate_notes

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
def _is_f9(key):
    return key == keyboard.Key.f9

class KeyboardManager:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.is_recording = False
        self.f9_pressed = False
        self.listener = None

    def process_audio_thread(self, file_path):
        try:
            print("\n⏳ 開始 STT 辨識...")
            start = time.time()
            transcript = transcribe_audio(file_path)
            print(f"✅ 辨識完成 ({time.time()-start:.1f}s): {transcript}")

            if not transcript or not transcript.strip():
                print("⚠️ 未偵測到有效語音。")
                return
            
            print("⏳ 開始 LLM 語意修飾...")
            start = time.time()
            refined_text = generate_notes(transcript)
            print(f"✅ 修飾完成 ({time.time()-start:.1f}s):\n{refined_text}")
            
            # 備份使用者原本的剪貼簿內容 (僅限文字)
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass
            
            # 替換為 AI 修飾後的文字
            pyperclip.copy(refined_text)
            time.sleep(0.5)  # 增加延遲，確保 Windows 剪貼簿已經準備好
            
            import pyautogui
            # 模擬送出 Ctrl+V
            pyautogui.hotkey('ctrl', 'v')
            print("✅ 文字已成功輸出至游標處！")
            
            # 等待 0.5 秒讓 Windows 完成貼上動作，然後神不知鬼不覺地把原本的剪貼簿還原！
            time.sleep(0.5)
            try:
                if original_clipboard:
                    pyperclip.copy(original_clipboard)
            except Exception:
                pass
            
        except Exception as e:
            print(f"❌ 處理錯誤: {e}")

    def on_press(self, key):
        try:
            if _is_f9(key):
                if not self.f9_pressed:
                    self.f9_pressed = True
                    
                    if not self.is_recording:
                        # 第一次按下：開始錄音
                        self.is_recording = True
                        print("\n🔴 錄音開始！請對麥克風說話...")
                        ui.msg_queue.put('show_floating')
                        self.recorder.start_recording()
                    else:
                        # 第二次按下：停止錄音
                        self.is_recording = False
                        print("⏹ 錄音結束，處理中...")
                        ui.msg_queue.put('hide_floating')
                        file_path = self.recorder.stop_recording()
                        
                        if file_path:
                            threading.Thread(
                                target=self.process_audio_thread,
                                args=(file_path,),
                                daemon=True
                            ).start()
        except Exception as e:
            print(f"❌ on_press 錯誤: {e}")

    def on_release(self, key):
        try:
            if _is_f9(key):
                self.f9_pressed = False
        except Exception as e:
            print(f"❌ on_release 錯誤: {e}")

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        print("🎧 全域快捷鍵監聽已啟動 (按住 Alt 錄音，鬆開 Alt 停止)")
