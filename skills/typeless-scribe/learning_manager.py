"""
NoType 自適應學習與糾錯管理器 (Active Learning & Correction Memory)
- 管理 corrections.json 糾錯映射庫 (例如 "實心營" -> "石星瑩")
- 自動將學習到的正確詞彙同步追加進 dictionary.txt
- 提供全域文字輸出前的物理層強制糾錯替換
"""
import os
import json
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORRECTIONS_FILE = os.path.join(BASE_DIR, "corrections.json")
DICTIONARY_FILE = os.path.join(BASE_DIR, "dictionary.txt")

def load_corrections() -> dict:
    if os.path.exists(CORRECTIONS_FILE):
        try:
            with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_corrections(corrections: dict):
    try:
        with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(corrections, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Learning] Error saving corrections: {e}")

def append_to_dictionary(word: str):
    """如果詞彙不在 dictionary.txt 中，自動追加至字典末尾"""
    word = word.strip()
    if not word or not os.path.exists(DICTIONARY_FILE):
        return
        
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 檢查是否已存在 (不分大小寫比對單詞)
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        if any(l.lower() == word.lower() for l in lines):
            return
            
        # 追加至檔案末尾
        with open(DICTIONARY_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{word}\n")
        print(f"[Learning] Added '{word}' to dictionary.txt")
    except Exception as e:
        print(f"[Learning] Error appending to dictionary: {e}")

def add_correction(wrong_text: str, correct_text: str, category: str = None):
    """
    新增一組糾錯記憶：
    1. 寫入 corrections.json
    2. 自動沉澱正確字詞至 dictionary.txt 中的指定分類
    """
    wrong_text = wrong_text.strip()
    correct_text = correct_text.strip()
    
    if not correct_text:
        return
        
    if wrong_text and wrong_text != correct_text:
        corrections = load_corrections()
        corrections[wrong_text] = correct_text
        save_corrections(corrections)
        print(f"[Learning] Learned correction: '{wrong_text}' -> '{correct_text}'")
        
    # 自動將正確詞彙記入專屬字典並精準歸類
    try:
        import dictionary_manager
        if not category:
            category = dictionary_manager.predict_category(correct_text)
        dictionary_manager.add_word(correct_text, category=category)
    except Exception as e:
        print(f"[Learning] Error adding to dictionary: {e}")
        append_to_dictionary(correct_text)

def apply_corrections(text: str) -> str:
    """套用所有已學習的糾錯記憶至文字中"""
    if not text:
        return text
        
    corrections = load_corrections()
    if not corrections:
        return text
        
    # 依長度降序排序，長詞優先匹配替換
    sorted_pairs = sorted(corrections.items(), key=lambda x: len(x[0]), reverse=True)
    
    for wrong, correct in sorted_pairs:
        if wrong in text:
            text = text.replace(wrong, correct)
            
    return text
