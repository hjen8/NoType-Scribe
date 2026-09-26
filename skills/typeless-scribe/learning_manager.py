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

def add_correction(wrong_text: str, correct_text: str, category: str = None, contexts: list = None):
    """
    新增一組糾錯記憶：
    1. 寫入 corrections.json (若有 contexts 則寫入結構化條件規則)
    2. 自動沉澱正確字詞至 dictionary.txt 中的指定分類
    """
    wrong_text = wrong_text.strip()
    correct_text = correct_text.strip()
    
    if not correct_text:
        return
        
    if wrong_text and wrong_text != correct_text:
        corrections = load_corrections()
        clean_contexts = [c.strip() for c in contexts if c and c.strip()] if contexts else []
        if clean_contexts:
            corrections[wrong_text] = {
                "correct": correct_text,
                "contexts": clean_contexts
            }
        else:
            corrections[wrong_text] = correct_text
        save_corrections(corrections)
        print(f"[Learning] Learned correction: '{wrong_text}' -> '{correct_text}' (contexts={clean_contexts})")
        
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
    """
    套用所有已學習的糾錯記憶至文字中
    - 導入子句級作用域隔離 (Clause-Level Scope)：以標點符號進行斷句切片，各子句獨立比對，徹底杜絕跨子句污染誤傷
    - 支援長詞優先、正向語境 (contexts) 與負向排除語境 (negative_contexts)
    """
    if not text:
        return text
        
    corrections = load_corrections()
    if not corrections:
        return text
        
    # 依長度降序排序，長詞/短語優先匹配替換 (Longer Words First)
    sorted_pairs = sorted(corrections.items(), key=lambda x: len(x[0]), reverse=True)
    
    # 子句級作用域隔離：使用常見標點符號與斷行進行子句切片
    # 使用捕獲組保留所有標點符號與換行空白，確保重建後 100% 還原原始排版
    clause_delimiters = r'([，。；！？、\n\r\t：,;:!?])'
    tokens = re.split(clause_delimiters, text)
    
    processed_tokens = []
    for token in tokens:
        if not token:
            continue
        # 若為分隔標點符號或純換行，直接原樣保留
        if re.fullmatch(clause_delimiters, token):
            processed_tokens.append(token)
            continue
            
        clause = token
        for wrong, rule in sorted_pairs:
            if isinstance(rule, dict):
                target_correct = rule.get("correct", "")
                pos_ctx = rule.get("contexts", [])
                neg_ctx = rule.get("negative_contexts", [])
                
                # 必須在同一子句中包含目標詞
                if wrong in clause:
                    # 檢查正向關鍵字 (若有定義則必須命中其一)
                    hit_pos = any(ctx in clause for ctx in pos_ctx) if pos_ctx else True
                    # 檢查負向排除關鍵字 (若命中任一則放棄替換，避免互殺)
                    hit_neg = any(n_ctx in clause for n_ctx in neg_ctx) if neg_ctx else False
                    
                    if hit_pos and not hit_neg:
                        clause = clause.replace(wrong, target_correct)
            else:
                if wrong in clause:
                    clause = clause.replace(wrong, str(rule))
        processed_tokens.append(clause)
        
    return "".join(processed_tokens)

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
    {"截距", "差距"},
    {"登錄", "登入"},
    {"申覆", "申訴"},
    {"核定", "核訂"},
    {"終止", "中止"},
    {"廢止", "廢除"},
    {"賦予", "付與"},
    {"及", "即"},
    {"副", "附"},
    {"須", "需"},
    {"度", "渡"},
    {"座", "坐"},
    {"制", "致"},
    {"意", "義"},
    {"象", "相"},
    {"部", "步"},
    {"辨", "辦", "辯"},
    {"絕", "決"},
    {"報", "暴"},
    {"公權力", "權利"},
    {"多項式", "多項是"},
    {"質數", "指數"},
    {"交集", "焦急"},
    {"係數", "細數"},
    {"題綱", "提綱"},
    {"常駐", "常住"},
    {"端點", "斷點"},
    {"相依", "相互"},
    {"真因", "基因"},
    {"心聲", "新生"},
    {"給予", "給與"},
    {"涵蓋", "含括"},
]

# 常見多義詞建議之語境關鍵詞（提供 Shift+F8 預填輔助）
RECOMMENDED_CONTEXTS = {
    ("全隊", "全對"): "考卷, 考試, 題目, 測驗, 答題, 滿分",
    ("全對", "全隊"): "球隊, 中華隊, 隊員, 團隊, 集合, 比賽",
    ("城市", "程式"): "代碼, 軟體, 開發, Python, 腳本, 執行, bug",
    ("程式", "城市"): "鄉鎮, 市區, 建築, 人口, 交通, 都會, 發展",
    ("在", "再"): "又, 一次, 見面, 說一遍, 考慮, 來一次",
    ("再", "在"): "家, 學校, 這裡, 那裡, 正在, 進行",
    ("權利", "權力"): "政治, 政府, 掌權, 統治, 國家, 機關",
    ("權力", "權利"): "義務, 人權, 法律, 享用, 保障, 侵犯",
    ("做", "作"): "作文, 作品, 作業, 作息, 作戰",
    ("作", "做"): "做事, 做好, 做飯, 做人, 做工",
    ("終點", "中點"): "線段, 三角形, 坐標, 距離, 幾何",
    ("中點", "終點"): "起點, 衝線, 跑步, 馬拉松, 比賽",
    ("截距", "捷徑"): "坐標, 直線, 斜率, 方程式, 函數",
    ("捷徑", "截距"): "抄, 近路, 快速, 方法, 走",
    ("制定", "制訂"): "計畫, 方案, 辦法, 草案, 合約, 細則",
    ("制訂", "制定"): "法律, 憲法, 法規, 政策, 條例",
    ("反應", "反映"): "民意, 問題, 意見, 陳情, 長官, 心聲",
    ("反映", "反應"): "化學, 物理, 熱烈, 生理, 刺激, 遲鈍",
    ("登入", "登錄"): "實價登錄, 成績登錄, 名冊, 登記",
    ("登錄", "登入"): "帳號, 密碼, 系統, 進入, 驗證",
    ("終止", "中止"): "暫停, 比賽中止, 中途, 暫時",
    ("中止", "終止"): "合約, 契約, 終止勞動, 永久結束",
    ("常住", "常駐"): "程式, 背景, 系統匣, Daemon, 執行",
    ("常駐", "常住"): "人口, 居民, 戶籍, 居住",
    ("基因", "真因"): "排查, 真因, 根本原因, 問題",
    ("真因", "基因"): "突變, 生物, 遺傳, DNA, 定序",
    ("新生", "心聲"): "傾聽, 心聲, 說出, 員工, 基層",
    ("心聲", "新生"): "訓練, 報到, 入學, 高一, 嬰兒",
}

def check_homophone_ambiguity(wrong_text: str, correct_text: str) -> dict:
    """
    檢測 (wrong_text, correct_text) 是否屬於依賴上下文之同音多義詞：
    - 若兩者命中多義詞庫，回傳 is_ambiguous=True、建議語境關鍵詞與明確警示
    """
    w = wrong_text.strip()
    c = correct_text.strip()
    if not w or not c or w == c:
        return {"is_ambiguous": False, "reason": "", "suggested_context": ""}
        
    for s in HOMOPHONE_AMBIGUITY_SETS:
        if w in s and c in s:
            suggested = RECOMMENDED_CONTEXTS.get((w, c), "")
            return {
                "is_ambiguous": True,
                "reason": f"「{w}」與「{c}」皆為常見合法詞彙（依前後文決定）",
                "suggested_context": suggested,
                "warning": f"⚠️ 警示：『{w}』與『{c}』皆為合法詞彙！請填寫下方「語境限制」或改用 Enter 單次替換",
                "popup_msg": (
                    f"「{w}」與「{c}」皆為合法常用詞彙！\n\n"
                    f"您尚未設定「語境限制關鍵詞」！\n"
                    f"若將其直接寫入永久全域糾錯，未來只要出現「{w}」，\n"
                    f"都會被強制無差別替換為「{c}」，極易引發其他語意的誤傷！\n\n"
                    f"建議取消並在「語境限制」欄位填入觸發關鍵詞（如 考卷, 考試），\n"
                    f"或改按 Enter 僅本次替換。\n\n"
                    f"確定仍要無條件強制全域替換嗎？"
                )
            }
            
    return {"is_ambiguous": False, "reason": "", "suggested_context": ""}

