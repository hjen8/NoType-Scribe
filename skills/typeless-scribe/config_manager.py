import json
import os

# 使用絕對路徑，確保開機啟動時即使工作目錄錯誤，也能找到 config.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

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

def get_api_key():
    config_key = load_config().get("GROQ_API_KEY", "")
    if config_key:
        return config_key
        
    # 如果 config 中沒有，試著從環境變數讀取 (相容於先前的 $env 設定)
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key:
        set_api_key(env_key)  # 自動寫入 config.json 以供永久儲存
        return env_key
        
    return ""

def set_api_key(api_key):
    config = load_config()
    config["GROQ_API_KEY"] = api_key
    save_config(config)
