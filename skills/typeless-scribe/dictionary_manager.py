"""
NoType 專屬字典管理器 (Dictionary Manager)
- 支援 dictionary.txt 的讀取、寫入、去重複
- 支援自適應編碼匯入 (UTF-8-BOM / UTF-8 / CP950 / GB18030)
- 支援「合併增補 (Merge)」與「完全覆蓋 (Overwrite)」雙模式
- 支援一鍵匯出為標準 UTF-8 文字檔
"""
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICTIONARY_FILE = os.path.join(BASE_DIR, "dictionary.txt")

HEADER_TEMPLATE = """# 在此輸入您的專屬詞彙，每行一個。
# AI 會優先參考這些詞彙來修正語音辨識。
# NoType 專屬字典
"""

def get_dictionary_path() -> str:
    """取得 dictionary.txt 絕對路徑"""
    return DICTIONARY_FILE

def ensure_dictionary_file():
    """確保 dictionary.txt 存在"""
    if not os.path.exists(DICTIONARY_FILE):
        try:
            with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
                f.write(HEADER_TEMPLATE)
        except Exception as e:
            print(f"[Dictionary] Error creating dictionary.txt: {e}")

def load_categorized_words() -> dict[str, list[str]]:
    """
    載入字典中依分類整理的詞彙字典：
    {
        "系統與工作流指令": ["開工", "收工", ...],
        "軟硬體、工具與擴充": ["S磁碟", ...],
        ...
    }
    """
    ensure_dictionary_file()
    categories = {}
    current_cat = "未分類專用詞"
    seen_all = set()
    
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    # 排除全域引導註解
                    if line.startswith("# 在此") or line.startswith("# AI") or line.startswith("# NoType") or line.startswith("# 總詞數") or line.startswith("# 由外部"):
                        continue
                    cat_name = line.lstrip("#").strip()
                    if cat_name:
                        current_cat = cat_name
                        if current_cat not in categories:
                            categories[current_cat] = []
                    continue
                
                lower_w = line.lower()
                if lower_w not in seen_all:
                    seen_all.add(lower_w)
                    if current_cat not in categories:
                        categories[current_cat] = []
                    categories[current_cat].append(line)
    except Exception as e:
        print(f"[Dictionary] Error loading categorized words: {e}")
        
    return categories

def save_categorized_words(cat_dict: dict[str, list[str]]) -> bool:
    """
    將結構化的分類字典寫回 dictionary.txt
    """
    ensure_dictionary_file()
    try:
        with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
            f.write("# 在此輸入您的專屬詞彙，每行一個。\n")
            f.write("# AI 會優先參考這些詞彙來修正語音辨識。\n\n")
            for cat, words in cat_dict.items():
                if not cat:
                    continue
                f.write(f"# {cat}\n")
                for w in words:
                    w = w.strip()
                    if w and not w.startswith("#"):
                        f.write(f"{w}\n")
                f.write("\n")
        return True
    except Exception as e:
        print(f"[Dictionary] Error saving categorized words: {e}")
        return False

def load_words() -> list[str]:
    """保持向後相容：回傳所有分類扁平化的唯一詞彙清單"""
    cats = load_categorized_words()
    words = []
    seen = set()
    for cat_words in cats.values():
        for w in cat_words:
            if w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
    return words

def get_categories() -> list[str]:
    """取得現有分類名稱清單"""
    cats = load_categorized_words()
    return list(cats.keys())

def add_word(word: str, category: str = None) -> bool:
    """新增單一詞彙至指定分類，若未指定則預設加入地理名詞或最後分類"""
    word = word.strip()
    if not word or word.startswith("#"):
        return False
        
    cats = load_categorized_words()
    for words in cats.values():
        if any(w.lower() == word.lower() for w in words):
            return False
            
    if category and category in cats:
        cats[category].append(word)
    elif cats:
        target_cat = category if category else "地理、數學與學術名詞"
        if target_cat not in cats:
            target_cat = list(cats.keys())[-1]
        cats.setdefault(target_cat, []).append(word)
    else:
        cats["其他常用專有名詞"] = [word]
        
    return save_categorized_words(cats)

def delete_word(word_to_delete: str) -> bool:
    """從 dictionary.txt 中刪除指定詞彙，保持分類結構完整"""
    word_to_delete = word_to_delete.strip().lower()
    cats = load_categorized_words()
    deleted = False
    for cat_name, words in cats.items():
        new_words = []
        for w in words:
            if w.lower() == word_to_delete:
                deleted = True
            else:
                new_words.append(w)
        cats[cat_name] = new_words
        
    if deleted:
        return save_categorized_words(cats)
    return False

def read_file_with_auto_encoding(filepath: str) -> list[str]:
    """
    以自適應編碼讀取外部文字檔案，依序嘗試：
    1. utf-8-sig (完美處理含 BOM 或無 BOM 之 UTF-8)
    2. utf-8
    3. cp950 (臺灣繁體 Big5)
    4. gb18030
    """
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'gb18030']
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                lines = [line.strip() for line in f]
            # 成功讀取且解析出內容
            return lines
        except (UnicodeDecodeError, LookupError):
            continue
            
    # 若都失敗，以忽略錯誤方式讀取
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f]

def import_dictionary(filepath: str, mode: str = "merge") -> tuple[int, int]:
    """
    從指定檔案匯入詞彙
    :param filepath: 外部文字檔案路徑
    :param mode: 'merge' (合併增補去重複) 或 'overwrite' (完全覆蓋)
    :return: (新增詞數, 目前字典總詞數)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"找不到匯入檔案: {filepath}")
        
    raw_lines = read_file_with_auto_encoding(filepath)
    new_words = []
    new_seen = set()
    
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lower_w = line.lower()
        if lower_w not in new_seen:
            new_seen.add(lower_w)
            new_words.append(line)
            
    if mode == "overwrite":
        # 完全覆蓋模式：重建 dictionary.txt
        with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
            f.write(HEADER_TEMPLATE)
            f.write(f"# 由外部匯入覆蓋 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
            for w in new_words:
                f.write(f"{w}\n")
        return len(new_words), len(new_words)
    else:
        # 合併增補模式 (預設)
        existing_words = load_words()
        existing_set = {w.lower() for w in existing_words}
        
        words_to_add = [w for w in new_words if w.lower() not in existing_set]
        
        if words_to_add:
            with open(DICTIONARY_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n# 由外部檔案匯入增補 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                for w in words_to_add:
                    f.write(f"{w}\n")
                    
        total_words = len(load_words())
        return len(words_to_add), total_words

def export_dictionary(target_path: str) -> int:
    """
    將目前的 dictionary.txt 匯出為標準 UTF-8 文字檔
    :param target_path: 目標儲存路徑
    :return: 匯出的詞彙總數
    """
    words = load_words()
    target_dir = os.path.dirname(os.path.abspath(target_path))
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(f"# NoType 專屬自訂詞庫匯出檔\n")
        f.write(f"# 匯出時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 總詞數: {len(words)} 筆\n\n")
        for w in words:
            f.write(f"{w}\n")
            
    return len(words)
