"""
NoType 歷史紀錄管理器
- 在記憶體中保存最近 100 筆語音辨識紀錄
- 程式重啟後自動清空（不落地持久化）
"""
import os
import time as _time
from datetime import datetime

MAX_RECORDS = 1000
AUDIO_DIR = r"S:\NoType_Audio"

def ensure_audio_dir():
    r"""確保 S:\NoType_Audio 目錄存在"""
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_audio_filename():
    """產生帶時間戳的音檔名，例如 20260920_123500.wav"""
    ensure_audio_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(AUDIO_DIR, f"{ts}.wav")

class HistoryRecord:
    __slots__ = ('timestamp', 'duration_sec', 'status', 'raw_text', 'refined_text', 'audio_path', 'error_msg')
    
    def __init__(self, duration_sec=0.0, status="success", raw_text="", refined_text="", audio_path="", error_msg=""):
        self.timestamp = datetime.now().strftime("%Y/%m/%d %p%I:%M").replace("AM", "上午").replace("PM", "下午")
        self.duration_sec = round(duration_sec, 1)
        self.status = status        # "success" | "failed"
        self.raw_text = raw_text
        self.refined_text = refined_text
        self.audio_path = audio_path
        self.error_msg = error_msg

# --- 全域紀錄池 (In-Memory) ---
_records: list = []

def add_record(record: HistoryRecord):
    """新增一筆紀錄到最前面，超過上限時自動刪除最舊的"""
    _records.insert(0, record)
    while len(_records) > MAX_RECORDS:
        old = _records.pop()
        # 刪除最舊紀錄對應的音檔
        if old.audio_path and os.path.exists(old.audio_path):
            try:
                os.remove(old.audio_path)
            except Exception:
                pass

def get_all() -> list:
    """取得全部紀錄（新 → 舊）"""
    return list(_records)

def get_count() -> int:
    return len(_records)
