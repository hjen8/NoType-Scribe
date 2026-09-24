"""
NoType 專屬字典管理器 (Dictionary Manager)
- 支援 Markdown 兩層結構 (# 大分類, ## 子分類)
- 支援分類上下順序調整 (move_category)
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

def load_hierarchy() -> list[dict]:
    """
    載入兩層結構的階層資料：
    [
        {
            "name": "系統與工作流指令",
            "words": ["開工", "收工", ...],
            "subcategories": []
        },
        {
            "name": "地理",
            "words": [],
            "subcategories": [
                {"name": "氣候水文與大氣", "words": [...]},
                {"name": "地形與地質", "words": [...]},
                {"name": "地圖GIS與人文經濟", "words": [...]}
            ]
        },
        ...
    ]
    """
    ensure_dictionary_file()
    hierarchy = []
    current_cat = None
    current_sub = None
    seen_all = set()
    
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    # 排除全域引導註解
                    if (line.startswith("# 在此") or line.startswith("# AI") or 
                        line.startswith("# NoType") or line.startswith("# 總詞數") or 
                        line.startswith("# 由外部") or line.startswith("# 匯出時間")):
                        continue
                    
                    if line.startswith("##"):
                        sub_name = line.lstrip("#").strip()
                        if not current_cat:
                            current_cat = {"name": "未分類大項", "words": [], "subcategories": []}
                            hierarchy.append(current_cat)
                        current_sub = {"name": sub_name, "words": []}
                        current_cat["subcategories"].append(current_sub)
                    else:
                        cat_name = line.lstrip("#").strip()
                        current_cat = {"name": cat_name, "words": [], "subcategories": []}
                        hierarchy.append(current_cat)
                        current_sub = None
                    continue
                
                lower_w = line.lower()
                if lower_w not in seen_all:
                    seen_all.add(lower_w)
                    if current_sub is not None:
                        current_sub["words"].append(line)
                    elif current_cat is not None:
                        current_cat["words"].append(line)
                    else:
                        current_cat = {"name": "未分類專用詞", "words": [line], "subcategories": []}
                        hierarchy.append(current_cat)
    except Exception as e:
        print(f"[Dictionary] Error loading hierarchy: {e}")
        
    return hierarchy

def save_hierarchy(hierarchy: list[dict]) -> bool:
    """將階層結構格式化寫入 dictionary.txt"""
    ensure_dictionary_file()
    try:
        with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
            f.write("# 在此輸入您的專屬詞彙，每行一個。\n")
            f.write("# AI 會優先參考這些詞彙來修正語音辨識。\n\n")
            for cat in hierarchy:
                cat_name = cat.get("name", "").strip()
                if not cat_name:
                    continue
                f.write(f"# {cat_name}\n")
                for w in cat.get("words", []):
                    w = w.strip()
                    if w and not w.startswith("#"):
                        f.write(f"{w}\n")
                if cat.get("words"):
                    f.write("\n")
                for sub in cat.get("subcategories", []):
                    sub_name = sub.get("name", "").strip()
                    if not sub_name:
                        continue
                    f.write(f"## {sub_name}\n")
                    for w in sub.get("words", []):
                        w = w.strip()
                        if w and not w.startswith("#"):
                            f.write(f"{w}\n")
                    f.write("\n")
        return True
    except Exception as e:
        print(f"[Dictionary] Error saving hierarchy: {e}")
        return False

def load_words() -> list[str]:
    """保持向後相容：回傳所有分類扁平化的唯一詞彙清單（提供 Whisper 與 LLM）"""
    h = load_hierarchy()
    words = []
    seen = set()
    for cat in h:
        for w in cat.get("words", []):
            if w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
        for sub in cat.get("subcategories", []):
            for w in sub.get("words", []):
                if w.lower() not in seen:
                    seen.add(w.lower())
                    words.append(w)
    return words

def load_categorized_words() -> dict[str, list[str]]:
    """向後相容：回傳扁平路徑對應詞彙列表"""
    h = load_hierarchy()
    flat = {}
    for cat in h:
        c_name = cat["name"]
        subs = cat.get("subcategories", [])
        if subs:
            for s in subs:
                flat[f"{c_name} / {s['name']}"] = list(s.get("words", []))
            if cat.get("words"):
                flat[c_name] = list(cat.get("words", []))
        else:
            flat[c_name] = list(cat.get("words", []))
    return flat

def get_categories() -> list[str]:
    """取得現有新增可用的分類路徑清單"""
    h = load_hierarchy()
    opts = []
    for cat in h:
        c_name = cat["name"]
        subs = cat.get("subcategories", [])
        if subs:
            for s in subs:
                opts.append(f"{c_name} / {s['name']}")
        else:
            opts.append(c_name)
    return opts

def add_word(word: str, category: str = None) -> bool:
    """新增單一詞彙至指定分類（支援 '地理 / 氣候水文與大氣' 或 '數學與學術名詞'）"""
    word = word.strip()
    if not word or word.startswith("#"):
        return False
        
    all_words = [w.lower() for w in load_words()]
    if word.lower() in all_words:
        return False
        
    h = load_hierarchy()
    added = False
    
    if category and " / " in category:
        parent_name, sub_name = category.split(" / ", 1)
        for cat in h:
            if cat["name"] == parent_name:
                for sub in cat.get("subcategories", []):
                    if sub["name"] == sub_name:
                        sub["words"].append(word)
                        added = True
                        break
                if not added:
                    cat.setdefault("subcategories", []).append({"name": sub_name, "words": [word]})
                    added = True
                break
    elif category:
        for cat in h:
            if cat["name"] == category:
                cat["words"].append(word)
                added = True
                break
                
    if not added:
        if h:
            if h[-1].get("subcategories"):
                h[-1]["subcategories"][-1]["words"].append(word)
            else:
                h[-1]["words"].append(word)
        else:
            h.append({"name": "常用專有名詞", "words": [word], "subcategories": []})
            
    return save_hierarchy(h)

def delete_word(word_to_delete: str) -> bool:
    """從階層中刪除指定詞彙"""
    word_to_delete = word_to_delete.strip().lower()
    h = load_hierarchy()
    deleted = False
    for cat in h:
        new_words = [w for w in cat.get("words", []) if w.lower() != word_to_delete]
        if len(new_words) != len(cat.get("words", [])):
            deleted = True
            cat["words"] = new_words
        for sub in cat.get("subcategories", []):
            new_sub_words = [w for w in sub.get("words", []) if w.lower() != word_to_delete]
            if len(new_sub_words) != len(sub.get("words", [])):
                deleted = True
                sub["words"] = new_sub_words
                
    if deleted:
        return save_hierarchy(h)
    return False

def move_category(cat_identifier: str, direction: str) -> bool:
    """
    上下移動分類排序：
    cat_identifier: 可能是大類名稱 "地理"，或是子類路徑 "地理 / 氣候水文與大氣"
    direction: "up" 或 "down"
    """
    h = load_hierarchy()
    if " / " in cat_identifier:
        parent_name, sub_name = cat_identifier.split(" / ", 1)
        for cat in h:
            if cat["name"] == parent_name:
                subs = cat.get("subcategories", [])
                for i, s in enumerate(subs):
                    if s["name"] == sub_name:
                        if direction == "up" and i > 0:
                            subs[i], subs[i-1] = subs[i-1], subs[i]
                            return save_hierarchy(h)
                        elif direction == "down" and i < len(subs) - 1:
                            subs[i], subs[i+1] = subs[i+1], subs[i]
                            return save_hierarchy(h)
                        return False
    else:
        for i, cat in enumerate(h):
            if cat["name"] == cat_identifier:
                if direction == "up" and i > 0:
                    h[i], h[i-1] = h[i-1], h[i]
                    return save_hierarchy(h)
                elif direction == "down" and i < len(h) - 1:
                    h[i], h[i+1] = h[i+1], h[i]
                    return save_hierarchy(h)
                return False
    return False

def read_file_with_auto_encoding(filepath: str) -> list[str]:
    """以自適應編碼讀取外部文字檔案"""
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'gb18030']
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                lines = [line.strip() for line in f]
            return lines
        except (UnicodeDecodeError, LookupError):
            continue
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f]

def import_dictionary(filepath: str, mode: str = "merge") -> tuple[int, int]:
    """從指定檔案匯入詞彙"""
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
        with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
            f.write(HEADER_TEMPLATE)
            f.write(f"# 由外部匯入覆蓋 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
            for w in new_words:
                f.write(f"{w}\n")
        return len(new_words), len(new_words)
    else:
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
    """將目前的 dictionary.txt 匯出為標準 UTF-8 文字檔"""
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
