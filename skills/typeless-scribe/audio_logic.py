import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import time as _time

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
            print(f"⚠️ 音訊警告: {status}")
        self.q.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.q = queue.Queue()
        self.start_time = _time.time()
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self.callback
        )
        self.stream.start()

    def stop_recording(self, output_filename="temp_recording.wav"):
        if not self.recording:
            return None
        
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        duration = _time.time() - self.start_time
        
        # 防呆：錄音時間太短，視為誤觸 Alt 鍵
        if duration < MIN_RECORD_SECONDS:
            print(f"⚠️ 錄音僅 {duration:.1f} 秒，低於 {MIN_RECORD_SECONDS} 秒門檻，已忽略（可能是誤觸）。")
            return None
        
        audio_data = []
        while not self.q.empty():
            audio_data.append(self.q.get())
            
        if not audio_data:
            print("⚠️ 沒有錄到任何聲音。")
            return None
            
        audio_data = np.concatenate(audio_data, axis=0)
        
        # 靜音偵測：若音量太低，跳過送 API
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms < SILENCE_THRESHOLD:
            print(f"⚠️ 音量過低 (RMS={rms:.4f})，未偵測到有效語音，已忽略。")
            return None
        
        sf.write(output_filename, audio_data, self.samplerate)
        print(f"⏹ 錄音結束 ({duration:.1f} 秒, RMS={rms:.4f})，已儲存暫存檔至 {output_filename}")
        return output_filename
