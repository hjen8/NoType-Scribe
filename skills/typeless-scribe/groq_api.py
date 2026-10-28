import os
import sys
from groq import Groq
from config_manager import (
    get_all_groq_keys, 
    get_current_groq_key, 
    rotate_groq_key, 
    get_gemini_api_key
)

def safe_print(*args, **kwargs):
    """Windows CP950 安全印出函式，杜絕 UnicodeEncodeError (如 emoji \u26a0, \U0001f4a1 等) 導致之例外中斷"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or 'cp950'
            safe_args = [
                str(a).encode(encoding, errors='replace').decode(encoding)
                for a in args
            ]
            print(*safe_args, **kwargs)
        except Exception:
            pass
    except Exception:
        pass

def get_client(api_key=None):
    key = api_key or get_current_groq_key()
    if not key:
        return None
    # 設置 timeout=6.0 與 max_retries=0，徹底杜絕 SDK 面對 429 時在後台 sleep 死等 20~70 秒之惡性卡頓，遭遇 429 立刻拋出由 NoType 毫秒級自動切換備援
    return Groq(api_key=key, timeout=6.0, max_retries=0)

def get_dictionary_words() -> str:
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dictionary.txt')
    if not os.path.exists(dict_path):
        return ""
    words = []
    with open(dict_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                words.append(line)
    return ", ".join(words)

def transcribe_audio(file_path: str, return_meta: bool = False):
    keys = get_all_groq_keys()
    
    custom_words = get_dictionary_words()
    prompt_text = "這是一段繁體中文逐字稿。"
    if custom_words:
        from learning_manager import load_corrections
        corrections = load_corrections()
        
        # 0. 【第 0 順位絕對先發】：日常系統與工作核心指令 (優先鎖死，100% 確保進駐 Whisper 前 50 bytes)
        command_priority = ["收工", "SOP", "Skill", "王貞云"]

        # 1. 【第一順位先發】：親友與學生精選人名 (37 詞，約 370 bytes，確保重要親友與學生人名 100% 入選)
        name_priority = []
        try:
            import dictionary_manager
            hierarchy = dictionary_manager.load_hierarchy()
            for cat in hierarchy:
                cat_name = cat.get("name", "")
                if any(k in cat_name for k in ["人名", "親友", "家人", "學生"]):
                    for nw in cat.get("words", []):
                        if nw not in name_priority and nw not in command_priority:
                            name_priority.append(nw)
        except Exception:
            pass
            
        # 2. 【第二順位先發】：核心電腦名詞、同音消歧義與自適應學習庫正確詞彙
        core_priority = ["S磁碟", "S碟", "磁碟", "程式", "磁碟機", "S槽", "主選單", "全對", "霈沄", "語昕"]
        for correct in corrections.values():
            target = correct if isinstance(correct, str) else correct.get("correct", "")
            if target and target not in core_priority and target not in name_priority and target not in command_priority:
                core_priority.append(target)
                
        dict_words = [w.strip() for w in custom_words.split(', ') if w.strip()]
        
        combined_words = []
        for w in command_priority + name_priority + core_priority + dict_words:
            if w not in combined_words:
                combined_words.append(w)
        
        selected = []
        base_prefix = "這是一段繁體中文逐字稿。"
        test_prefix = base_prefix + " 常見詞："
        curr_bytes = len(test_prefix.encode('utf-8'))
        MAX_SAFE_BYTES = 405  # 實測黃金上限：380 bytes (精準容納 34 詞)，徹底杜絕注意力稀釋，確保「收工」孤島短指令原生 100% 識別！
        
        for w in combined_words:
            w_bytes = len(w.encode('utf-8')) + 2  # 包含 ", " 2 bytes
            if curr_bytes + w_bytes > MAX_SAFE_BYTES:
                break
            selected.append(w)
            curr_bytes += w_bytes
            
        if selected:
            prompt_text = test_prefix + ", ".join(selected)
        else:
            prompt_text = base_prefix

    last_err = None
    # 1. 嘗試雲端 Groq Whisper
    if keys:
        for _ in range(max(1, len(keys))):
            client = get_client()
            if not client:
                break
            try:
                with open(file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(os.path.basename(file_path), file.read()),
                        model="whisper-large-v3",
                        prompt=prompt_text,
                        response_format="text",
                        language="zh"
                    )
                return (transcription, False) if return_meta else transcription
            except Exception as e:
                err_str = str(e)
                last_err = e
                # 若為 Prompt 過長或無效 Prompt 錯誤 (HTTP 400 invalid_prompt)，立即以極簡 Prompt 自動降級重試，絕不中斷辨識
                if "prompt" in err_str.lower() or "400" in err_str:
                    safe_print(f"[STT] Detected prompt issue ({err_str[:60]}), falling back to minimal prompt...")
                    try:
                        with open(file_path, "rb") as file:
                            transcription = client.audio.transcriptions.create(
                                file=(os.path.basename(file_path), file.read()),
                                model="whisper-large-v3",
                                prompt="這是一段繁體中文逐字稿。",
                                response_format="text",
                                language="zh"
                            )
                        return (transcription, False) if return_meta else transcription
                    except Exception as fallback_err:
                        last_err = fallback_err
                        safe_print(f"[STT] Minimal prompt fallback failed: {fallback_err}")
                
                safe_print(f"[STT] Failed ({err_str[:40]}...), rotating key...")
                if len(keys) > 1:
                    rotate_groq_key()
                else:
                    break

    # 2. 雲端失敗或無網路時，觸發地端 Faster-Whisper 極限備援 (Local Faster-Whisper Fallback)
    safe_print(f"[STT Fallback] ⚠️ 雲端語音辨識不可用 ({last_err or '無有效 API Key'})，無縫啟動地端 Faster-Whisper 備援...")
    try:
        from local_transcribe import local_transcriber
        local_text = local_transcriber.transcribe(file_path, prompt=prompt_text)
        if local_text and local_text.strip():
            safe_print("[STT Fallback] ✅ 地端語音辨識成功！")
            return (local_text, True) if return_meta else local_text
    except Exception as local_err:
        safe_print(f"[STT Fallback] 地端語音辨識亦發生異常: {local_err}")

    # 若地端亦失敗，再拋出詳細異常
    if not keys:
        raise ValueError("NEED_KEY: 缺少 GROQ_API_KEY，且地端備援未能處理。")
    err_msg = str(last_err)
    if "401" in err_msg or "invalid_api_key" in err_msg:
        raise ValueError("NEED_KEY: Groq API Key 無效，請檢查設定。")
    elif "429" in err_msg or "rate_limit" in err_msg:
        raise RuntimeError("💡 NoType 提示：Groq 每日額度已達上限 (429)，請稍候再試。")
    raise last_err

_cached_models = []
_model_penalties = {}  # {model_name: penalty_until_timestamp}

def penalize_model(model_name: str, duration: int = 60):
    """將遭遇 429、超時或異常的模型暫時打入冷宮降權，優先由其他高速模型接替 (Groq TPM 為 1 分鐘滾動窗口，預設處罰 60 秒)"""
    import time
    _model_penalties[model_name] = time.time() + duration
    print(f"[Groq] 模型 {model_name} 已列入降權處罰名單，{duration} 秒內不作第一首選")

def get_active_chat_models(client, force_refresh=False) -> list:
    global _cached_models
    import time
    now = time.time()
    
    preferred_order = [
        "qwen/qwen3.8-27b",          # 實測 0.25s 極速，中文繁體能力極佳且配額充裕
        "llama-3.3-70b-versatile",   # 70B 旗艦 (若帳號開放即納入前線)
        "llama-3.1-8b-instant",      # 8B 極速 (若帳號開放即納入前線)
        "openai/gpt-oss-120b",       # 0.8s 備援，大容量配額
        "groq/compound",
        "groq/compound-mini",
        "openai/gpt-oss-20b"         # 降至末端備援 (TPM 僅 8k，易爆 429)
    ]
    
    if _cached_models and not force_refresh:
        valid = [m for m in _cached_models if _model_penalties.get(m, 0) <= now]
        penalized = [m for m in _cached_models if _model_penalties.get(m, 0) > now]
        return valid + penalized
    
    discovered = []
    try:
        remote_models = client.models.list()
        all_ids = [m.id for m in remote_models.data]
        
        # 排除語音、防護欄 (Guardrail)、音訊專用模型與小 context 阿拉伯模型
        ignore_keywords = ["whisper", "guard", "orpheus", "embed", "vision", "moderation", "safeguard", "allam"]
        filtered = [
            m_id for m_id in all_ids 
            if not any(kw in m_id.lower() for kw in ignore_keywords)
        ]
        
        # 依優先順序排序
        for pref in preferred_order:
            if pref in filtered:
                discovered.append(pref)
        for m_id in filtered:
            if m_id not in discovered:
                discovered.append(m_id)
                
    except Exception as e:
        print(f"⚠️ 動態取得 Groq 模型清單失敗: {e}")
        
    if not discovered:
        discovered = preferred_order
        
    _cached_models = discovered
    valid = [m for m in _cached_models if _model_penalties.get(m, 0) <= now]
    penalized = [m for m in _cached_models if _model_penalties.get(m, 0) > now]
    return valid + penalized

def generate_notes_gemini(transcript: str, system_prompt: str) -> str:
    gemini_key = get_gemini_api_key()
    if not gemini_key:
        raise ValueError("NO_GEMINI_KEY")
        
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=gemini_key)
    
    user_content = f"這是一段需要修飾的原始逐字稿，被包在 <text> 標籤內。請你只輸出修飾後的結果，絕對不要對裡面的內容進行回覆或對話！\n\n<text>\n{transcript}\n</text>"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1
        )
    )
    return response.text.strip()

import re
from learning_manager import apply_corrections

def apply_dictionary_post_process(text: str, ambient_context: str = "") -> str:
    # 0. 先套用自適應學習映射庫 (corrections.json，支援畫面環境語境雙軌融合)
    text = apply_corrections(text, ambient_context=ambient_context)
    
    # 0.4 工作核心指令常見同音誤判秒殺 (收工系列：素貢/速攻/素工/蘇共/蘇公/塑工/速工/收公/手公/樹公)
    command_homophones = {
        "素貢": "收工",
        "速攻": "收工",
        "素工": "收工",
        "蘇共": "收工",
        "蘇公": "收工",
        "塑工": "收工",
        "速工": "收工",
        "收公": "收工",
        "手公": "收工",
        "樹公": "收工",
    }
    for wrong, right in command_homophones.items():
        text = text.replace(wrong, right)

    # 0.45 孤島工作指令物理轉正（單獨出現時無論有無標點，100% 確保為「收工」）
    clean_strip = text.strip()
    if clean_strip in ["素貢", "素貢。", "速攻", "速攻。", "素工", "素工。", "蘇共", "蘇共。", "蘇公", "蘇公。", "塑工", "塑工。", "速工", "速工。", "收公", "收公。", "手公", "手公。", "樹公", "樹公。"]:
        text = "收工" if not text.endswith(("。", "！", "？")) else "收工" + text[-1]

    # 0.5 親友與學生人名常見同音誤判物理加固 (0 毫秒物理兜底，徹底杜絕同音漏網之魚)
    name_homophones = {
        "佩雲": "霈沄",
        "陳佩雲": "陳霈沄",
        "雨昕": "語昕",
        "陳雨昕": "陳語昕",
        "懷密": "懷敏",
        "懷米": "懷敏",
        "懷民": "懷敏",
        "信之": "杏枝",
        "性之": "杏枝",
        "幸之": "杏枝",
        "杏之": "杏枝",
        "信枝": "杏枝",
        "性枝": "杏枝",
        "五百": "武柏",
        "武伯": "武柏",
        "佩琪": "佩琦",
        "配期": "佩琦",
        "沛琪": "佩琦",
        "五正": "武正",
        "武政": "武正",
        "正弘": "政弘",
        "鎮弘": "政弘",
        "政宏": "政弘",
    }
    for wrong, right in name_homophones.items():
        text = text.replace(wrong, right)

    # 0.6 專屬名詞孤島物理兜底（當單獨出現時保障「爸爸葯」不被誤寫為「爸爸要」）
    clean_strip = text.strip()
    if clean_strip in ["爸爸要", "爸爸要。", "爸爸要！", "爸爸要？"]:
        text = "爸爸葯"
    
    custom_words = get_dictionary_words()
    if not custom_words:
        return text
        
    words = [w.strip() for w in custom_words.split(', ') if w.strip()]
    
    # 1. 繁簡/異體字與台灣在地慣用語硬性校正 (物理保險層)
    taiwan_lexicon = {
        "復盤": "覆盤",
        "視頻": "影片",
        "軟件": "軟體",
        "硬件": "硬體",
        "網絡": "網路",
        "服務器": "伺服器",
        "打印": "列印",
        "默認": "預設",
        "登錄": "登入",
        "激活": "啟用",
        "鏈接": "連結",
        "激光": "雷射",
        "高清": "高畫質",
        "內存": "記憶體",
        "進程": "行程",
        "S 詞疊": "S磁碟",
        "S詞疊": "S磁碟",
        "詞疊": "磁碟",
        "磁疊": "磁碟",
        "刺碟": "磁碟",
        "S 疊": "S碟",
        "S疊": "S碟",
        "SDA": "S碟",
        "竹選單": "主選單",
        "金要": "金鑰",
        "更號": "根號",
        "多項是": "多項式",
        "借時": "屆時",
        "賬號": "帳號",
        "記賬": "記帳",
        "結賬": "結帳",
        "字本": "治本",
        "字標": "治標",
        "此對": "詞對",
        "詞隊": "詞對",
        "磁隊": "詞對",
        "磁組": "詞組",
        "常住程式": "常駐程式",
        "站高一段落": "暫告一段落",
        "站告一段落": "暫告一段落",
        "站告": "暫告",
        "代辦事項": "待辦事項",
        "代辦清單": "待辦清單",
        "代辦工作": "待辦工作",
        "代辦任務": "待辦任務",
        "代辦日程": "待辦日程",
    }
    for mainland, tw in taiwan_lexicon.items():
        text = text.replace(mainland, tw)
    # 數字量詞同音口誤微整與中英數排版 (例如 2字本 -> 2 治本、1字標 -> 1 治標)
    text = re.sub(r'(\d+)\s*(?:字本|治本)', r'\1 治本', text)
    text = re.sub(r'(\d+)\s*(?:字標|治標)', r'\1 治標', text)
    # 防重複前綴替換 (避免將已轉為「演算法」的詞再度替換為「演演算法」)
    text = re.sub(r'(?<!演)算法', '演算法', text)
    
    # 1.5 常見電腦操作語境同音字修正 (例如「這個城市能夠...」->「這個程式能夠...」)
    text = re.sub(r'這個城市(?=能夠|可以|會|跑|執行|運作|軟體)', '這個程式', text)
    text = re.sub(r'(寫|執行|重啟|啟動|常駐|關閉|我們的)城市', r'\1程式', text)
    
    # 2. 專屬英數字詞彙大小寫強制校正 (例如 skill -> Skill, sop -> SOP)
    for w in words:
        if re.match(r'^[A-Za-z0-9_.\-]+$', w):
            # 確保單詞或邊界比對
            pattern = re.compile(rf'(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])', re.IGNORECASE)
            text = pattern.sub(w, text)
            
    return text

def generate_notes(transcript: str, on_model_switch=None, app_mode: str = 'general', ambient_context: str = "") -> str:
    groq_keys = get_all_groq_keys()
    
    # 0. 快速指令先行轉正 (若 STT 直接命中指令同音誤判，先行轉正避免 LLM 腦補)
    cmd_fast = {
        "素貢": "收工", "速攻": "收工", "素工": "收工", "蘇共": "收工",
        "蘇公": "收工", "塑工": "收工", "速工": "收工", "收公": "收工",
        "手公": "收工", "樹公": "收工"
    }
    for wrong, right in cmd_fast.items():
        transcript = transcript.replace(wrong, right)
    if transcript.strip() in ["素貢", "速攻", "素工", "蘇共", "蘇公", "塑工", "速工", "收公", "手公", "樹公"]:
        transcript = "收工"
    
    system_prompt = (
        "你是一個『語音辨識逐字稿修飾助理』，不是聊天機器人。\n"
        "任務要求：\n"
        "1. 【標點與流暢】：加上正確繁體中文標點符號，修正錯字，使語句通順。\n"
        "2. 【智慧條列清單】：當內容為待辦、代辦、清單、採買、步驟流程或列舉多項重點時，強制換行並以垂直阿拉伯數字編號排版（如 1. 2. 3. ），每項獨立一行。\n"
        "3. 【單句無句號】：若僅為單一短句（無逗號等斷句），結尾絕對不要加句號；兩句以上複合語句結尾正常加句號。\n"
        "4. 【數字與單位標準化】：數值、年份、百分比、金額或度量衡，自動整理為半形阿拉伯數字與規範符號（如 250 元、80%、3.5 公分）。\n"
        "5. 【中英數混排排版】：中文與英數混排時保持標準間隔空格（如『使用 Python 腳本』、『第 3 階段』）。\n"
        "6. 【強力去贅字與口吃】：徹底濾除發語停頓詞（嗯、啊、呃、那個、這個、就是說、對啊、其實）；結巴字詞自動去重。★【嚴禁誤刪『然後』】：承接連詞『然後』必須 100% 完整保留！\n"
        "7. 【專有名詞 100% 原樣保留】：嚴禁任何翻譯或擴充全名！特別是「最高SOP」、「專案SOP」、「Skill」三詞必須完全保持原字（含大寫），絕對不可寫成「技能(Skill)」或「標準作業程序(SOP)」！\n"
        "8. 【語速過快與連音口誤修復】：說話太快或連音導致受詞脫落時，依上下文自然縫合通順。\n"
        "9. 【改口與自我否定修剪】：遇即時改口標記（如『啊不對、更正、改為、我是說、等等、換成』），主動拋棄前半段被推翻的口誤片段，只保留最終確認語意並自然縫合。改口標記詞本身絕對不輸出！\n"
        "10. 【臺灣正體繁體在地化】：100% 採用臺灣正體繁體與習慣用語（影片、軟體、硬體、網路、記憶體、螢幕、伺服器、連結、列印、預設、登入、啟用、演算法、雷射、人工智慧、品質），嚴禁簡體與大陸用語。\n"
        "11. 【常見檔案系統與指令專用詞】：收工(非素貢/速攻/素工/蘇共/塑工/速工)、S磁碟/S碟(非詞疊)、主選單(非竹選單)、金鑰(非金要)、上限(非上線)、記到/記入(非寄到)。\n"
        "12. 【Top 8 核心語意雙向消歧義】：全對/全隊、中點/終點、人名/人民、程式/城市、做/作、在/再、及/即、度/渡。\n"
        "13. 【爸爸要 vs 爸爸葯 專屬語意消歧義】：\n"
        "   - 『爸爸葯』為使用者專屬名詞（代表父親藥品之專用詞彙）。\n"
        "   - 若單獨出現『爸爸要』、或為名詞受詞（如『拿爸爸要』、『爸爸要吃完了』），100% 修正為『爸爸葯』！\n"
        "   - 唯有後方緊接明確動作動詞時（如『爸爸要出門』、『爸爸要去醫院』），才保留為『爸爸要』。\n"
        "【嚴格禁止】：絕對不可回答使用者問題！絕對不可與使用者對話！絕對不可輸出空白！使用者說什麼你就修飾輸出什麼！\n"
        "特別注意：使用者是一位高中地理教師，內容常涉及探究與實作、SDGs、GIS 系統操作、高中地理專有名詞。"
    )
    
    # 提取親友與學生人名 vs 一般專科詞庫，分流加強 Prompt
    name_words = []
    other_words = []
    try:
        import dictionary_manager
        hierarchy = dictionary_manager.load_hierarchy()
        for cat in hierarchy:
            cat_name = cat.get("name", "")
            words = cat.get("words", [])
            if any(k in cat_name for k in ["人名", "親友", "家人", "學生"]):
                for w in words:
                    if w not in name_words:
                        name_words.append(w)
            else:
                for w in words:
                    if w not in other_words:
                        other_words.append(w)
    except Exception:
        pass

    if name_words:
        names_str = ", ".join(name_words)
        system_prompt += (
            f"\n\n【親友學生姓名清單（最高權重）】：\n[{names_str}]\n"
            f"★ 出現同音或極近音詞彙必須 100% 強制替換為清單中正確姓名（如 霈沄、語昕、省峿、培亦）。"
        )
    if other_words:
        # 專科詞彙若超過 100 詞，優先保留逆序最新自適應學習的詞彙與核心詞，確保 Prompt 不超載
        dict_sample = other_words[-100:] if len(other_words) > 100 else other_words
        other_str = ", ".join(dict_sample)
        system_prompt += (
            f"\n\n【專科領域與專有名詞清單】：\n[{other_str}]\n"
            f"遇發音相同、同音異字或大小寫不同，一律修正為字典規範（只輸出純文字修飾結果，禁多餘說明）。"
        )
        
    # 依當前前景視窗 App 模式動態微調修飾風格 (App-Aware Dynamic Tone Adaptation)
    app_tone_instructions = {
        "chat": (
            "\n\n【目前應用情境：即時通訊社交軟體 (LINE / 微信 / Discord)】：\n"
            "使用者正在傳送私訊或群組聊天。輸出語氣請保持『親切口語、自然輕鬆、明快通暢』；"
            "適度保留自然口語語助詞（如：好喔、收到、哈哈、沒問題），標點符號自然簡約，切忌過度嚴肅或八股公文腔！"
        ),
        "email": (
            "\n\n【目前應用情境：商務電子郵件 / 團隊協作 (Outlook / Teams / Slack)】：\n"
            "使用者正在撰寫商務訊息或正式電子郵件。輸出語氣請保持『專業得體、禮貌規範、文法嚴謹』；"
            "具備商務溝通禮儀，標點符號規範清晰。"
        ),
        "doc": (
            "\n\n【目前應用情境：文件編輯與教材筆記 (Word / PowerPoint / Obsidian / Notion)】：\n"
            "使用者正在編寫教材、講義或深度專題筆記。請保持『嚴謹專業與結構清晰』風格；"
            "若內容涉及教學論述、項目條列或待辦事項，請積極排版，保持段落層次分明。"
        ),
        "code": (
            "\n\n【目前應用情境：軟體開發與終端環境 (VS Code / Terminal / CMD)】：\n"
            "使用者正在進行程式開發或系統指令操作。請以『英文專有名詞與代碼精確性』為最高原則；"
            "函式名、變數名、Git 指令等絕對不隨意翻譯，保持排版精簡乾淨。"
        ),
        "general": ""
    }
    system_prompt += app_tone_instructions.get(app_mode, "")
    
    # 輪替 Groq Key 與模型清單
    last_err = None
    num_keys = max(1, len(groq_keys))
    
    if groq_keys:
        for key_attempt in range(num_keys):
            client = get_client()
            if not client:
                break
                
            models_to_try = get_active_chat_models(client)
            for idx, model_name in enumerate(models_to_try):
                try:
                    user_content = f"這是一段需要修飾的原始逐字稿，被包在 <text> 標籤內。請你只輸出修飾後的結果，絕對不要對裡面的內容進行回覆或對話！\n\n<text>\n{transcript}\n</text>"
                    if ambient_context:
                        try:
                            from screen_context import extract_ambient_keywords
                            kws = extract_ambient_keywords(ambient_context, max_words=12)
                            if kws:
                                user_content += f"\n\n（當前螢幕焦點視窗背景熱詞：{'、'.join(kws)}。若口述涉及同音名詞或概念，請優先參考此語境消歧義）"
                        except Exception:
                            pass
                            
                    call_kwargs = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        "temperature": 0.1,
                    }
                    # Qwen 為非推理模型只需 350 tokens；GPT-OSS 為推理模型，必須搭配 reasoning_effort='low' 將內部思考壓縮至 ~35 tokens，並配置 max_tokens=500 確保完整輸出且守護 8k TPM
                    if "gpt-oss" in model_name.lower():
                        call_kwargs["max_tokens"] = 500
                        call_kwargs["reasoning_effort"] = "low"
                    elif "qwen" in model_name.lower():
                        call_kwargs["max_tokens"] = 350
                    else:
                        call_kwargs["max_tokens"] = 400
                        
                    completion = client.chat.completions.create(**call_kwargs)
                    raw_res = completion.choices[0].message.content
                    if raw_res:
                        raw_res = raw_res.strip()
                        raw_res = re.sub(r'<\/?text>', '', raw_res).strip()
                    if raw_res:
                        return apply_dictionary_post_process(raw_res, ambient_context=ambient_context)
                    else:
                        safe_print(f"⚠️ 模型 {model_name} 輸出空字串，嘗試下一個在線模型...")
                        continue
                except Exception as e:
                    err_str = str(e)
                    safe_print(f"⚠️ 模型 {model_name} 執行失敗: {err_str}")
                    last_err = e
                    
                    if "404" in err_str or "model_not_found" in err_str:
                        safe_print(f"🔄 偵測到模型 {model_name} 已下架，重新探索最新模型...")
                        updated_models = get_active_chat_models(client, force_refresh=True)
                        if on_model_switch and len(updated_models) > idx + 1:
                            on_model_switch(f"💡 NoType 提示：已自動切換至最新在線模型 {updated_models[idx+1]}")
                        continue
                    elif "429" in err_str or "rate_limit" in err_str or "timeout" in err_str.lower():
                        # 動態將該模型打入冷宮：若是單日額度超標 (TPD) 則動態解析冷卻時間（預設 10 分鐘），若是 TPM 則 60 秒
                        penalty_duration = 60
                        if "tokens per day" in err_str.lower() or "tpd" in err_str.lower():
                            penalty_duration = 600
                            m = re.search(r'try again in\s*(?:(\d+)m)?(?:([\d.]+)s)?', err_str)
                            if m:
                                mins = float(m.group(1)) if m.group(1) else 0
                                secs = float(m.group(2)) if m.group(2) else 0
                                parsed = mins * 60 + secs
                                if parsed > 0:
                                    penalty_duration = min(parsed + 5, 3600)
                        penalize_model(model_name, duration=penalty_duration)
                        # 若當前 Key 還有其他備用模型，優先嘗試下一個在線模型 (例如 70B 受限換 8B)
                        if idx < len(models_to_try) - 1:
                            safe_print(f"🔄 模型 {model_name} 觸發速率限制，立刻切換至下一個在線模型...")
                            continue
                        elif len(groq_keys) > 1:
                            rotate_groq_key()
                            if on_model_switch:
                                on_model_switch("💡 NoType 提示：當前金鑰額度已滿，已自動輪替至備用金鑰")
                            break
                    elif "401" in err_str or "invalid_api_key" in err_msg if 'err_msg' in locals() else False:
                        if len(groq_keys) > 1:
                            rotate_groq_key()
                            break
                    continue
                    
    # 若 Groq 全部失敗或無 Key，嘗試啟動方案 C：Gemini 雙保險備援
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            safe_print("🔄 啟動 Gemini 雙保險備援修飾...")
            res = generate_notes_gemini(transcript, system_prompt)
            if res and res.strip():
                if on_model_switch:
                    on_model_switch("💡 NoType 提示：Groq 暫時受限，已無縫啟動 Gemini 雙保險備援")
                return apply_dictionary_post_process(res.strip(), ambient_context=ambient_context)
            else:
                safe_print("⚠️ Gemini 備援回傳空字串")
        except Exception as ge:
            safe_print(f"⚠️ Gemini 備援亦失敗: {ge}")
            
    # 若完全沒有設定 Key
    if not groq_keys and not gemini_key:
        raise ValueError("NEED_KEY: 尚未設定 API Key，請在彈出的設定視窗中貼上金鑰。")
        
    # 若在線模型皆未回傳非空字串（無拋出例外），啟動極限物理保險回退至原始逐字稿
    if not last_err and transcript and transcript.strip():
        safe_print("⚠️ 所有在線模型皆未產出非空文字，自動降級使用原始逐字稿保險")
        return apply_dictionary_post_process(transcript.strip(), ambient_context=ambient_context)
        
    err_msg = str(last_err)
    if "429" in err_msg or "rate_limit" in err_msg:
        raise RuntimeError("💡 NoType 提示：Groq 每日額度已達上限 (429)，請稍候 10 分鐘再試。")
    elif "401" in err_msg or "invalid_api_key" in err_msg:
        raise ValueError("NEED_KEY: API Key 無效，請在彈出的設定視窗中檢查金鑰。")
    else:
        raise RuntimeError(f"⚠️ 服務異常: {err_msg[:60]}")
