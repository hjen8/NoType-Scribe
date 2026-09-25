import json
import os

# 使用絕對路徑，確保開機啟動時即使工作目錄錯誤，也能找到 config.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

_current_key_idx = 0

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    try:
        from backup_manager import sync_to_backup
        sync_to_backup()
    except Exception:
        pass


def parse_keys_list(raw_keys) -> list:
    if not raw_keys:
        return []
    if isinstance(raw_keys, list):
        return [k.strip() for k in raw_keys if k and k.strip()]
    # 支援逗號、分號、換行分隔
    delims = [',', ';', '\n', '\r']
    text = str(raw_keys)
    for d in delims:
        text = text.replace(d, ' ')
    return [k.strip() for k in text.split() if k.strip()]

def get_all_groq_keys() -> list:
    config = load_config()
    raw = config.get("GROQ_API_KEY", "")
    keys = parse_keys_list(raw)
    if keys:
        return keys
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key:
        keys = parse_keys_list(env_key)
        if keys:
            set_api_key(env_key)
            return keys
    return []

def get_current_groq_key() -> str:
    global _current_key_idx
    keys = get_all_groq_keys()
    if not keys:
        return ""
    if _current_key_idx >= len(keys):
        _current_key_idx = 0
    return keys[_current_key_idx]

def rotate_groq_key() -> str:
    global _current_key_idx
    keys = get_all_groq_keys()
    if len(keys) <= 1:
        return ""
    _current_key_idx = (_current_key_idx + 1) % len(keys)
    print(f"🔄 已輪替至第 {_current_key_idx + 1}/{len(keys)} 組 Groq API Key")
    return keys[_current_key_idx]

def get_api_key() -> str:
    return get_current_groq_key()

def set_api_key(api_key):
    config = load_config()
    config["GROQ_API_KEY"] = api_key
    save_config(config)

def get_gemini_api_key() -> str:
    config = load_config()
    cfg_key = config.get("GEMINI_API_KEY", "").strip()
    if cfg_key:
        return cfg_key
    return os.environ.get("GEMINI_API_KEY", "").strip()

def set_gemini_api_key(api_key):
    config = load_config()
    config["GEMINI_API_KEY"] = api_key
    save_config(config)

import datetime

def get_student_reminder_status() -> dict:
    config = load_config()
    reminder = config.get("STUDENT_REMINDER", {})
    if not isinstance(reminder, dict):
        reminder = {}
    return {
        "last_reminded_year": reminder.get("last_reminded_year", 0),
        "snoozed_until": reminder.get("snoozed_until", "")
    }

def set_student_reminder_done(year: int = None):
    if year is None:
        year = datetime.date.today().year
    config = load_config()
    reminder = config.get("STUDENT_REMINDER", {})
    if not isinstance(reminder, dict):
        reminder = {}
    reminder["last_reminded_year"] = int(year)
    reminder["snoozed_until"] = ""
    config["STUDENT_REMINDER"] = reminder
    save_config(config)

def set_student_reminder_snooze(days: int = 7):
    snooze_date = datetime.date.today() + datetime.timedelta(days=days)
    config = load_config()
    reminder = config.get("STUDENT_REMINDER", {})
    if not isinstance(reminder, dict):
        reminder = {}
    reminder["snoozed_until"] = snooze_date.isoformat()
    config["STUDENT_REMINDER"] = reminder
    save_config(config)

def should_prompt_student_reminder(force_check_month: int = None) -> bool:
    today = datetime.date.today()
    month = today.month if force_check_month is None else force_check_month
    # 每年 6 月 (學期末/新學年度交接期)
    if month != 6:
        return False
    
    status = get_student_reminder_status()
    # 如果今年已經確認過，不再提醒
    if status["last_reminded_year"] >= today.year:
        return False
        
    # 如果設定了稍後提醒 (Snooze)，檢查是否尚未到期
    snooze_str = status.get("snoozed_until", "")
    if snooze_str:
        try:
            snooze_date = datetime.date.fromisoformat(snooze_str)
            if today < snooze_date:
                return False
        except Exception:
            pass
            
    return True

