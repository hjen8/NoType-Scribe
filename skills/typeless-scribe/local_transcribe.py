import os
import sys
import time
import threading
import gc
from groq_api import safe_print

class LocalWhisperTranscriber:
    """
    離線地端語音轉錄引擎 (Faster-Whisper 輕量化極限備援)
    - 採用 CTranslate2 CPU int8 量化推理，平時零記憶體佔用 (Lazy Loading)
    - 支援 10 分鐘閒置自動卸載與垃圾回收 (Idle Auto-Unload)，保護系統記憶體
    - 支援 initial_prompt 注入學生與親友人名名單，確保離線時人名精準
    """
    def __init__(self, model_size="base", idle_timeout_sec=600):
        self.model_size = model_size
        self.idle_timeout_sec = idle_timeout_sec
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(self.base_dir, "models", f"faster-whisper-{model_size}")
        self.model = None
        self._lock = threading.Lock()
        self._idle_timer = None

    def _reset_idle_timer(self):
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None
        
        def _unload_worker():
            with self._lock:
                if self.model is not None:
                    safe_print(f"[LocalWhisper] Idle timeout ({self.idle_timeout_sec}s) reached. Unloading model from RAM...")
                    del self.model
                    self.model = None
                    gc.collect()
                    safe_print("[LocalWhisper] Memory cleanly reclaimed.")

        self._idle_timer = threading.Timer(self.idle_timeout_sec, _unload_worker)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _load_model_if_needed(self):
        with self._lock:
            if self.model is None:
                start_t = time.time()
                safe_print(f"[LocalWhisper] Lazy loading Faster-Whisper '{self.model_size}' model into RAM (CPU int8)...")
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=self.model_dir,
                    local_files_only=True
                )
                safe_print(f"[LocalWhisper] Model loaded in {time.time() - start_t:.2f}s.")

    def transcribe(self, audio_path: str, prompt: str = None) -> str:
        """
        執行地端語音轉錄。
        :param audio_path: 音訊檔案絕對路徑 (.wav)
        :param prompt: 專屬人名與字典提示詞 (相容 Whisper initial_prompt)
        :return: 轉錄純文字字串
        """
        if not os.path.exists(audio_path):
            safe_print(f"[LocalWhisper] Audio file not found: {audio_path}")
            return ""

        self._load_model_if_needed()
        self._reset_idle_timer()

        start_t = time.time()
        safe_print(f"[LocalWhisper] Transcribing {os.path.basename(audio_path)} locally...")

        # 構建繁體中文優先之 initial_prompt
        full_prompt = "以下是繁體中文語音輸入："
        if prompt:
            full_prompt += f" {prompt}"

        try:
            segments, info = self.model.transcribe(
                audio_path,
                language="zh",
                initial_prompt=full_prompt,
                beam_size=5,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            result_text = "".join(text_parts).strip()
            elapsed = time.time() - start_t
            safe_print(f"[LocalWhisper] Done ({elapsed:.2f}s, lang={info.language}): '{result_text}'")
            return result_text

        except Exception as e:
            safe_print(f"[LocalWhisper] Local transcribe error: {e}")
            raise e

    def is_loaded(self) -> bool:
        """檢查模型當前是否已加載於記憶體中"""
        return self.model is not None

    def manual_unload(self):
        """手動立即釋放模型記憶體"""
        with self._lock:
            if self._idle_timer:
                self._idle_timer.cancel()
                self._idle_timer = None
            if self.model is not None:
                del self.model
                self.model = None
                gc.collect()
                safe_print("[LocalWhisper] Model manually unloaded.")

# 全域單例
local_transcriber = LocalWhisperTranscriber()
