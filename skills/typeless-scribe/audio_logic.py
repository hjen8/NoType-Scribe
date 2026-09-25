import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import time as _time
from history_manager import generate_audio_filename

# 最短錄音秒數，低於此值視為誤觸，不送 API
MIN_RECORD_SECONDS = 0.8
# 靜音門檻 (RMS 低於此值視為無人說話)
SILENCE_THRESHOLD = 0.005

class AudioRecorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.q = queue.Queue()
        self.recording = False
        self.stream = None
        self.start_time = 0

    def callback(self, indata, frames, time, status):
        if status:
            print(f"[Audio] warning: {status}")
        self.q.put(indata.copy())

    def reset_audio_engine(self):
        """重置底層 PortAudio 引擎與當前錄音串流 (用於休眠喚醒或裝置插拔時)"""
        try:
            if self.stream is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            self.recording = False
            
            # 強制終止並重啟 PortAudio，刷新 Windows 音訊端點快取
            if hasattr(sd, '_terminate') and hasattr(sd, '_initialize'):
                sd._terminate()
                sd._initialize()
            print("[Audio] Sounddevice & PortAudio pipeline successfully reinitialized.")
            return True
        except Exception as e:
            print(f"[Audio] Reinitialize audio pipeline failed: {e}")
            return False

    def start_recording(self):
        self.recording = True
        self.q = queue.Queue()
        self.start_time = _time.time()
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                callback=self.callback
            )
            self.stream.start()
        except Exception as e:
            print(f"[Audio] Failed to open InputStream ({e}), triggering self-healing reset...")
            # 發生例外時，自動重置 PortAudio 引擎並重試一次 (隨需自癒)
            if self.reset_audio_engine():
                _time.sleep(0.05)
                self.recording = True
                self.stream = sd.InputStream(
                    samplerate=self.samplerate,
                    channels=self.channels,
                    callback=self.callback
                )
                self.stream.start()
                print("[Audio] Self-healing succeeded: InputStream started on second attempt.")
            else:
                raise e

    def stop_recording(self):
        """停止錄音，回傳 (file_path, duration_sec) 或 (None, 0)"""
        if not self.recording:
            return None, 0
        
        self.recording = False
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        
        duration = _time.time() - self.start_time
        
        # 防呆：錄音時間太短，視為誤觸 Alt 鍵
        if duration < MIN_RECORD_SECONDS:
            print(f"[Audio] Recording only {duration:.1f}s, below {MIN_RECORD_SECONDS}s threshold, ignored.")
            return None, 0
        
        audio_data = []
        while not self.q.empty():
            audio_data.append(self.q.get())
            
        if not audio_data:
            print("[Audio] No audio data captured.")
            return None, 0
            
        audio_data = np.concatenate(audio_data, axis=0)
        
        # 靜音偵測：若音量太低，跳過送 API
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms < SILENCE_THRESHOLD:
            print(f"[Audio] Volume too low (RMS={rms:.4f}), ignored.")
            return None, 0
        
        # 儲存到 S:\NoType_Audio\ 帶時間戳
        output_path = generate_audio_filename()
        sf.write(output_path, audio_data, self.samplerate)
        print(f"[Audio] Recorded {duration:.1f}s (RMS={rms:.4f}) -> {output_path}")
        return output_path, round(duration, 1)
