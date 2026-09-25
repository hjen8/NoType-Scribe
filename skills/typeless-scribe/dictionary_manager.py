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
        try:
            from backup_manager import sync_to_backup
            sync_to_backup()
        except Exception:
            pass
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

def edit_word(old_word: str, new_word: str, new_category: str = None) -> bool:
    """
    修改指定詞彙之內容或變更所屬分類
    """
    old_word = old_word.strip()
    new_word = new_word.strip()
    if not old_word or not new_word or new_word.startswith("#"):
        return False
        
    h = load_hierarchy()
    
    # 尋找舊詞所在位置
    old_cat_parent = None
    old_sub = None
    old_list = None
    old_idx = -1
    
    for cat in h:
        for idx, w in enumerate(cat.get("words", [])):
            if w.lower() == old_word.lower():
                old_cat_parent = cat
                old_list = cat["words"]
                old_idx = idx
                break
        if old_list is not None:
            break
        for sub in cat.get("subcategories", []):
            for idx, w in enumerate(sub.get("words", [])):
                if w.lower() == old_word.lower():
                    old_cat_parent = cat
                    old_sub = sub
                    old_list = sub["words"]
                    old_idx = idx
                    break
            if old_list is not None:
                break
        if old_list is not None:
            break
            
    if old_list is None:
        return False
        
    curr_cat_path = f"{old_cat_parent['name']} / {old_sub['name']}" if old_sub else old_cat_parent['name']
    
    # 若未換分類，原地修改文字保持順序
    if not new_category or new_category == curr_cat_path:
        old_list[old_idx] = new_word
        return save_hierarchy(h)
    else:
        # 分類搬遷：從原分類移除，放入新分類
        old_list.pop(old_idx)
        target_list = None
        if " / " in new_category:
            target_p, target_s = new_category.split(" / ", 1)
            for cat in h:
                if cat["name"] == target_p:
                    for sub in cat.get("subcategories", []):
                        if sub["name"] == target_s:
                            target_list = sub["words"]
                            break
                    if target_list is None:
                        cat.setdefault("subcategories", []).append({"name": target_s, "words": []})
                        target_list = cat["subcategories"][-1]["words"]
                    break
        else:
            for cat in h:
                if cat["name"] == new_category:
                    target_list = cat["words"]
                    break
            if target_list is None:
                h.append({"name": new_category, "words": [], "subcategories": []})
                target_list = h[-1]["words"]
                
        target_list.append(new_word)
        return save_hierarchy(h)

def move_word(word: str, category_path: str, direction: str) -> bool:
    """
    在指定分類內部上下移動詞彙順序：
    direction: "up" 或 "down"
    """
    word = word.strip().lower()
    h = load_hierarchy()
    target_words = None
    
    if " / " in category_path:
        parent_name, sub_name = category_path.split(" / ", 1)
        for cat in h:
            if cat["name"] == parent_name:
                for sub in cat.get("subcategories", []):
                    if sub["name"] == sub_name:
                        target_words = sub.get("words", [])
                        break
                break
    else:
        for cat in h:
            if cat["name"] == category_path:
                target_words = cat.get("words", [])
                break
                
    if not target_words:
        return False
        
    for i, w in enumerate(target_words):
        if w.lower() == word:
            if direction == "up" and i > 0:
                target_words[i], target_words[i-1] = target_words[i-1], target_words[i]
                return save_hierarchy(h)
            elif direction == "down" and i < len(target_words) - 1:
                target_words[i], target_words[i+1] = target_words[i+1], target_words[i]
                return save_hierarchy(h)
            return False
    return False

def predict_category(word: str) -> str:
    """
    依據詞彙特徵進行語意分類預測，回傳最相符的分類路徑
    """
    if not word:
        return "生活、金融與其他常用專有名詞"
    w = word.strip()
    
    # 1. 地理特徵
    climate_kw = ['流', '潮', '風', '雨', '雲', '雪', '冰', '氣候', '大氣', '聖嬰', '水', '海', '河', '波', '集中度', '逆溫', '環流', '西風', '熱帶', '溫帶']
    if any(k in w for k in climate_kw):
        return "地理 / 氣候水文與大氣"
    terrain_kw = ['地形', '地質', '山', '谷', '丘', '崖', '階', '原', '島', '峰', '嶺', '洞', '穴', '斷層', '背斜', '向斜', '地塹', '地壘', '喀斯特', '曲流', '鐘乳石', '沙洲', '石柱']
    if any(k in w for k in terrain_kw):
        return "地理 / 地形與地質"
    gis_kw = ['投影', 'gis', 'dtm', 'dem', '分析', '經濟', '農業', '工業', '人口', '中地', '商閾', '等高線', '金字塔', '區位']
    if any(k in w.lower() for k in gis_kw):
        return "地理 / 地圖GIS與人文經濟"
        
    # 2. 學校班級教學
    school_kw = ['班', '校', '課', '卷', '考', '題', '學', '國中', '高中', '小學', '老師', '同學', '學習', '講義', '模考', '學測', '會考', '段考', '景女', 'cmgsh']
    if any(k in w.lower() for k in school_kw):
        return "學校、班級與教學"
        
    # 3. 軟硬體工具與擴充
    tech_kw = ['py', 'api', 'key', 'exe', 'app', '軟體', '硬體', '程式', '腳本', '槽', '碟', '檔', '庫', 'ui', 'tool', 'sop', 'skill', 'notype', 'git', 'windows', 'token']
    if any(k in w.lower() for k in tech_kw):
        return "軟硬體、工具與擴充"
        
    # 4. 系統指令
    cmd_kw = ['開工', '收工', '指令', '模式', '重啟', '關閉', '清空']
    if any(k in w for k in cmd_kw):
        return "系統與工作流指令"
        
    # 5. 家人與親友
    family_kw = ['媽', '爸', '哥', '姐', '弟', '妹', '親', '友', '叔', '伯', '阿姨', '姑', '舅', '金枝', '小溱', '懷斌', '女兒', '兒子', '老婆', '先生']
    if any(k in w for k in family_kw):
        return "家人與親友"
        
    # 6. 人名 (常見臺灣姓氏開頭且長度 2~4)
    tw_surnames = ['陳', '林', '黃', '張', '李', '王', '吳', '劉', '蔡', '楊', '許', '鄭', '謝', '洪', '郭', '邱', '曾', '廖', '賴', '徐', '周', '葉', '蘇', '莊', '江', '呂', '何', '羅', '高', '蕭', '潘', '朱', '簡', '鍾', '彭', '游', '詹', '胡', '施', '沈', '方', '柯']
    if 2 <= len(w) <= 4 and any(w.startswith(s) for s in tw_surnames):
        return "學生、同事與人名"
        
    # 7. 數學
    math_kw = [
        '加', '減', '乘', '除', '極值', '根號', '函數', '幾何', '代數', '方程式', '向量', '對稱', 
        '微積分', '矩陣', '多項式', '項式', '項是', '係數', '因式', '餘式', '展開', '斜率', 
        '坐標', '數列', '級數', '機率', '期望值', '排列', '組合', '正弦', '餘弦', '正切', 
        '三角', '橢圓', '雙曲線', '拋物線', '圓錐曲線', '不等式', '對數', '指數', 
        'log', 'sin', 'cos', 'tan', 'lim', 'sigma'
    ]
    if any(k in w.lower() for k in math_kw):
        return "數學與學術名詞"

        
    return "生活、金融與其他常用專有名詞"

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
