"""
NoType 歷史紀錄管理器
- 本地 JSON 持久化儲存 (最多保存最近 1000 筆)
- 程式重啟或系統關機後自動載入，紀錄永不丟失
"""
import os
import json
import time as _time
from datetime import datetime

MAX_RECORDS = 1000
AUDIO_DIR = r"S:\NoType_Audio"
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")

def ensure_audio_dir():
    r"""確保 S:\NoType_Audio 目錄存在並自動設定為隱藏資料夾 (+h)"""
    if not os.path.exists(AUDIO_DIR):
        try:
            os.makedirs(AUDIO_DIR, exist_ok=True)
        except Exception:
            pass
    if os.path.exists(AUDIO_DIR):
        try:
            import ctypes
            # FILE_ATTRIBUTE_HIDDEN = 0x02
            attrs = ctypes.windll.kernel32.GetFileAttributesW(AUDIO_DIR)
            if attrs != -1 and not (attrs & 2):
                ctypes.windll.kernel32.SetFileAttributesW(AUDIO_DIR, attrs | 2)
        except Exception:
            pass

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

def _load_history_from_disk() -> list:
    """從 history.json 載入持久化歷史紀錄"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            records = []
            for item in data:
                rec = HistoryRecord(
                    duration_sec=item.get("duration_sec", 0.0),
                    status=item.get("status", "success"),
                    raw_text=item.get("raw_text", ""),
                    refined_text=item.get("refined_text", ""),
                    audio_path=item.get("audio_path", ""),
                    error_msg=item.get("error_msg", "")
                )
                rec.timestamp = item.get("timestamp", rec.timestamp)
                records.append(rec)
            return records[:MAX_RECORDS]
    except Exception as e:
        print(f"[History] Error loading history from disk: {e}")
        return []

def _save_history_to_disk(records: list):
    """將歷史紀錄儲存至 history.json"""
    try:
        data = []
        for r in records[:MAX_RECORDS]:
            data.append({
                "timestamp": r.timestamp,
                "duration_sec": r.duration_sec,
                "status": r.status,
                "raw_text": r.raw_text,
                "refined_text": r.refined_text,
                "audio_path": r.audio_path,
                "error_msg": r.error_msg
            })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[History] Error saving history to disk: {e}")

# --- 全域紀錄池 (啟動時自動從磁碟載入) ---
_records: list = _load_history_from_disk()

def add_record(record: HistoryRecord):
    """新增一筆紀錄到最前面，並即時持久化儲存到磁碟"""
    _records.insert(0, record)
    while len(_records) > MAX_RECORDS:
        old = _records.pop()
        # 刪除超過上限之紀錄對應的音檔
        if old.audio_path and os.path.exists(old.audio_path):
            try:
                os.remove(old.audio_path)
            except Exception:
                pass
    _save_history_to_disk(_records)

def get_all() -> list:
    """取得全部紀錄（新 → 舊）"""
    return list(_records)

def get_count() -> int:
    return len(_records)
