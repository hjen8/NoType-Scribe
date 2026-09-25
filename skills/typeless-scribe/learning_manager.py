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
        try:
            from backup_manager import sync_to_backup
            sync_to_backup()
        except Exception:
            pass
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

# =====================================================
#  同音多義與上下文依賴詞彙偵測 (Homophone Ambiguity Guard)
# =====================================================
# 常見高度依賴前後文之同音多義詞對 (雙向皆為合法獨立詞彙，單獨物理替換易引發全域誤傷)
HOMOPHONE_AMBIGUITY_SETS = [
    {"全隊", "全對"},
    {"城市", "程式"},
    {"在", "再"},
    {"的", "得", "地"},
    {"權利", "權力"},
    {"制定", "制訂"},
    {"反應", "反映"},
    {"必須", "必需"},
    {"做", "作"},
    {"紀錄", "記錄"},
    {"公布", "公佈"},
    {"報到", "報導"},
    {"戴", "帶"},
    {"副", "付", "負"},
    {"度過", "渡過"},
    {"截止", "截至"},
    {"發奮", "發憤"},
    {"年青", "年輕"},
    {"急躁", "急燥"},
    {"法治", "法制"},
    {"公理", "功利"},
    {"導向", "倒向"},
    {"終點", "中點"},
    {"事蹟", "事跡"},
    {"交代", "交待"},
    {"啟示", "啟事"},
    {"意向", "意象", "異象"},
    {"事務", "事物"},
    {"包含", "飽含"},
    {"布置", "佈置"},
    {"化裝", "化妝"},
    {"定貨", "訂貨"},
    {"界線", "界限"},
    {"截距", "捷徑"},
]

def check_homophone_ambiguity(wrong_text: str, correct_text: str) -> dict:
    """
    檢測 (wrong_text, correct_text) 是否屬於依賴上下文之同音多義詞：
    - 若兩者命中多義詞庫，回傳 is_ambiguous=True 以及明確的警示文字與彈窗說明
    """
    w = wrong_text.strip()
    c = correct_text.strip()
    if not w or not c or w == c:
        return {"is_ambiguous": False, "reason": ""}
        
    for s in HOMOPHONE_AMBIGUITY_SETS:
        if w in s and c in s:
            return {
                "is_ambiguous": True,
                "reason": f"「{w}」與「{c}」皆為常見合法詞彙（依前後文決定）",
                "warning": f"⚠️ 警示：『{w}』與『{c}』皆為常見合法詞彙（依前後文決定）！\n建議使用 Enter（僅本次替換），切勿永久學習，避免全域誤傷！",
                "popup_msg": (
                    f"「{w}」與「{c}」皆為合法常用詞彙！\n\n"
                    f"若將其寫入永久糾錯庫，未來在所有語境中只要出現「{w}」，\n"
                    f"都會被強制無差別替換為「{c}」，極易引發其他語意的誤傷！\n\n"
                    f"確定仍要將其永久寫入糾錯庫嗎？\n"
                    f"(建議點選『否』，改用 Enter 僅本次替換)"
                )
            }
            
    return {"is_ambiguous": False, "reason": ""}

