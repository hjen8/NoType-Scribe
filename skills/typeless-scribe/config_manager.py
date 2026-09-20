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
