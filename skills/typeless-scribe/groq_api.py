import os
from groq import Groq
from config_manager import (
    get_all_groq_keys, 
    get_current_groq_key, 
    rotate_groq_key, 
    get_gemini_api_key
)

def get_client(api_key=None):
    key = api_key or get_current_groq_key()
    if not key:
        return None
    return Groq(api_key=key)

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

def transcribe_audio(file_path: str) -> str:
    keys = get_all_groq_keys()
    if not keys:
        raise ValueError("NEED_KEY: 缺少 GROQ_API_KEY，請設定金鑰。")
    
    custom_words = get_dictionary_words()
    prompt_text = "這是一段繁體中文逐字稿。"
    if custom_words:
        from learning_manager import load_corrections
        corrections = load_corrections()
        
        # 1. 優先詞庫：核心電腦名詞 + 自適應學習庫中的正確詞彙
        high_priority = ["S磁碟", "S碟", "磁碟", "程式", "磁碟機", "S槽", "SOP", "Skill"]
        for correct in corrections.values():
            if correct not in high_priority:
                high_priority.append(correct)
                
        dict_words = [w.strip() for w in custom_words.split(', ') if w.strip()]
        # 字典逆序（最新沉澱的詞最優先）
        reversed_dict = list(reversed(dict_words))
        
        combined_words = []
        for w in high_priority + reversed_dict + dict_words:
            if w not in combined_words:
                combined_words.append(w)
                
        selected = []
        curr_len = len(prompt_text)
        for w in combined_words:
            if curr_len + len(w) + 2 > 420:
                break
            selected.append(w)
            curr_len += len(w) + 2
        if selected:
            prompt_text += " 常見詞：" + ", ".join(selected)

    last_err = None
    # 嘗試所有可用的 Groq Keys
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
            return transcription
        except Exception as e:
            err_str = str(e)
            last_err = e
            print(f"[STT] Failed ({err_str[:40]}...), rotating key...")
            if len(keys) > 1:
                rotate_groq_key()
            else:
                break
                
    err_msg = str(last_err)
    if "401" in err_msg or "invalid_api_key" in err_msg:
        raise ValueError("NEED_KEY: Groq API Key 無效，請檢查設定。")
    elif "429" in err_msg or "rate_limit" in err_msg:
        raise RuntimeError("💡 NoType 提示：Groq 每日額度已達上限 (429)，請稍候再試。")
    raise last_err

_cached_models = []

def get_active_chat_models(client, force_refresh=False) -> list:
    global _cached_models
    if _cached_models and not force_refresh:
        return _cached_models
    
    preferred_order = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "groq/compound-mini",
        "groq/compound",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]
    
    discovered = []
    try:
        remote_models = client.models.list()
        all_ids = [m.id for m in remote_models.data]
        
        # 排除語音、防護欄 (Guardrail)、音訊專用模型
        ignore_keywords = ["whisper", "guard", "orpheus", "embed", "vision", "moderation", "safeguard"]
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
    print(f"[Groq] Active models: {_cached_models}")
    return _cached_models

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

def apply_dictionary_post_process(text: str) -> str:
    # 0. 先套用自適應學習映射庫 (corrections.json)
    text = apply_corrections(text)
    
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
        "S 詞疊": "S磁碟",
        "S詞疊": "S磁碟",
        "詞疊": "磁碟",
        "S 疊": "S碟",
        "S疊": "S碟",
        "SDA": "S碟",
    }
    for mainland, tw in taiwan_lexicon.items():
        text = text.replace(mainland, tw)
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

def generate_notes(transcript: str, on_model_switch=None, app_mode: str = 'general') -> str:
    groq_keys = get_all_groq_keys()
    
    system_prompt = (
        "你是一個『語音辨識逐字稿修飾助理』，不是聊天機器人。\n"
        "任務要求：\n"
        "1. 將使用者說的逐字稿加上正確的繁體中文標點符號，並修正錯字、讓語句通順。\n"
        "2. 【智慧分行與條列式清單 (Smart List Formatting)】：\n"
        "   - 核心原則：當使用者說話內容屬於『交辦事項、代辦清單、採買項目、步驟流程或列舉多項重點』時（例如出現：待辦、清單、第一、第二、還有、以及、買、準備、重點如下等詞彙），請【強制換行並以垂直條列式編號排版】！\n"
        "   - 排版規範：每個列舉項目必須獨立一行（包含實體換行符號 \\n），開頭使用阿拉伯數字加句點（例如 `1. `、`2. `、`3. `），若有前導句則在前導句末尾加上冒號，各條列項目末尾不需加句號。\n"
        "   - 條列清單對比範例：\n"
        "     * 範例 1（採買清單）：\n"
        "       - 輸入：『今天下午要去超市買牛奶、全麥麵包、還有五顆蘋果。』\n"
        "       - 輸出：\n"
        "今天下午要去超市買：\n"
        "1. 牛奶\n"
        "2. 全麥麵包\n"
        "3. 5 顆蘋果\n"
        "     * 範例 2（工作與會議待辦）：\n"
        "       - 輸入：『明天的處室會議有三個待辦事項，第一確認段考命題範圍，第二排定監考名單，第三收齊各科講義。』\n"
        "       - 輸出：\n"
        "明天的處室會議有 3 個待辦事項：\n"
        "1. 確認段考命題範圍\n"
        "2. 排定監考名單\n"
        "3. 收齊各科講義\n"
        "3. 【單句無句號】：如果使用者說的話只有「單一一個句子」（中間沒有逗號等斷句），無論字數長短，請絕對不要在結尾加上句號。但如果內容包含兩句以上的語句（中間有標點斷開），則請在結尾正常加上句號。\n"
        "4. 【數字與單位標準化】：涉及數值、年份、百分比、金額或計量單位時，自動整理為標準半形阿拉伯數字與規範符號（例如：『兩百五十塊』-> 250 元；『百分之八十』-> 80%；『三點五公分』-> 3.5 公分）。\n"
        "5. 【中英數混排排版美學】：中文與英文單字、阿拉伯數字混排時，請保持標準的間隔空格（例如：『使用 Python 腳本』、『針對 SDGs 目標』、『第 3 階段』），使排版清晰專業。\n"
        "6. 【強力去贅字與口頭禪清剿 (Aggressive Filler Stripping)】：\n"
        "   - 核心原則：徹底濾除說話時無意識的口頭禪、思考停頓詞與打結重複字，讓輸出的文字乾淨得如同精心撰寫的正式文稿！\n"
        "   - 思考停頓詞清剿（一律強制刪除，絕不輸出）：『嗯、啊、呃、那個、這個、就是、就是說、對啊、其實』若出現在句首作為思考發語詞或句中停頓，【一律強制剔除】！\n"
        "   - 『然後』濫用降噪：台灣口語極常把『然後、然後呢』當作口頭禪與無意義換氣詞。除非句意嚴格具備前後時間先後次序，否則句首或頻繁連續出現的『然後』必須【主動刪除或轉化為自然標點】！\n"
        "   - 口吃打結去重：字詞重複打結（如『我…我想說』->『我想說』；『這個這個問題』->『這個問題』）必須全自動合成為單一正確詞。\n"
        "   - 去贅字對比範例：\n"
        "     * 範例 1：『呃…那個…其實我們今天要討論的…嗯…就是高二的課程。』-> 輸出『我們今天要討論高二的課程』\n"
        "     * 範例 2：『然後我們就先看第一章，然後再看第二章，然後最後做總結。』-> 輸出『我們先看第一章，再看第二章，最後做總結。』\n"
        "     * 範例 3：『好，那…就是說…這個政策的影響其實很大。』-> 輸出『這個政策的影響很大』\n"
        "7. 【專有名詞 100% 原樣保留】：使用者極度反感任何形式的「翻譯、括號解釋或全名擴充」！特別是「最高SOP」、「專案SOP」、「Skill」這三個詞，必須完全保持原字（含大寫）！\n"
        "   - 聽到 Skill，就只准輸出「Skill」，絕對不可寫成「技能」、「技能(Skill)」或小寫「skill」！\n"
        "   - 聽到 SOP，就只准輸出「SOP」，絕對不可寫成「標準作業程序」或「標準作業程序(SOP)」！\n"
        "8. 【語速過快與連音口誤之語意修復】：當使用者說話念太快、出現連音或口誤導致受詞脫落或虛字錯用時（例如『你要找的又要幹嘛』語意上明顯為『你要找這個/找它又要幹嘛』），請根據整句話的前後文與自然語法，主動修復為流暢通順的自然語句。\n"
        "9. 【自我否定與口頭改口修剪 (False-Start Pruning)】：\n"
        "   - 核心原則：當使用者在說話時出現口誤、自我否定或即時改口標記（例如：『啊不對、不對、不是、更正、改為、我是說、沒有啦、等等、換成』）時，AI 必須展現『讀空氣』意圖理解能力，【主動拋棄前半段被推翻或否決的口誤片段】，並將最終拍板的決定與前半段未被否決的主詞/受詞進行自然語意縫合，只保留最終確認的完整語意！\n"
        "   - 關鍵硬性規定：所有的改口標記詞（如『更正、啊不對、等等、改為、我是說』）本身【絕對禁止輸出】在最終結果中！\n"
        "   - 語意縫合與修剪範例：\n"
        "     * 範例 1（時間改口）：『我們約明天下午三點…啊不對…改五點好了』-> 輸出『我們約明天下午 5 點』\n"
        "     * 範例 2（局部數值改口與主詞保留）：『總共要買五個蘋果…等等…買十個好了』-> 輸出『總共要買 10 個蘋果』\n"
        "     * 範例 3（時限改口與主詞保留）：『這篇文章的 deadline 是今天下午…更正…是下週一中午十二點』-> 輸出『這篇文章的 deadline 是下週一中午 12 點』\n"
        "     * 範例 4（對象改口）：『這個檔案寄給張主任…不是…寄給李組長』-> 輸出『這個檔案寄給李組長』\n"
        "     * 範例 5（名詞改口）：『打開那個 Word…啊不是…打開 PowerPoint』-> 輸出『打開 PowerPoint』\n"
        "10. 【台灣正體繁體與在地化慣用語 (Taiwan Localization)】：\n"
        "    - 輸出必須 100% 採用臺灣正體繁體中文語法與習慣用詞，絕對禁止輸出簡體字或中國大陸腔調習慣用語！\n"
        "    - 大陸慣用語強制在地化轉譯：\n"
        "      * 視頻 -> 影片；軟件 -> 軟體；硬件 -> 硬體；網絡 -> 網路\n"
        "      * 內存 -> 記憶體；屏幕 -> 螢幕；服務器 -> 伺服器；鏈接 -> 連結\n"
        "      * 打印 -> 列印；默認 -> 預設；登錄 -> 登入；激活 -> 啟用\n"
        "      * 算法 -> 演算法；激光 -> 雷射；人工智能 -> 人工智慧\n"
        "      * 質量 -> 品質（當指代品質、水準時；物理學之質量 mass 除外）\n"
        "11. 【常見電腦與檔案系統同音字/口誤智慧校正】：\n"
        "    - 「詞疊 / 磁疊 / 刺碟」-> 100% 強制修正為「磁碟」（特別在『S磁碟、C磁碟、磁碟機、檔案、目錄、RAMDISK』等電腦語境）。\n"
        "    - 「S疊 / S跌 / S蝶 / SDA」-> 100% 強制修正為「S碟」或「S磁碟」。\n"
        "    - 「城市」在軟體、執行、代碼、操作語境下（例如『希望我們這個程式能夠...』、『後台運行的程式』、『撰寫程式』）-> 必須強制修正為「程式」，絕非地理名詞『城市』！\n"
        "【嚴格禁止】：絕對不可以回答使用者的問題！絕對不可以跟使用者對話！絕對不可以擅自摘要未被否決的有效內容！\n"
        "使用者說什麼，你就輸出什麼（僅做錯字修正、口頭改口修剪、標點、數字標準化、贅詞去重與列舉排版）。\n"
        "特別注意：使用者是一位高中地理教師，內容常涉及『探究與實作』課程、SDGs (例如 5 種角色扮演設定)、"
        "GIS 系統操作、以及高中地理專有名詞。"
    )
    
    custom_words = get_dictionary_words()
    if custom_words:
        system_prompt += (
            f"\n\n【專屬字典強制替換】：\n"
            f"以下是使用者常說的專有名詞與詞庫清單：\n[{custom_words}]\n"
            f"只要發現逐字稿中有與字典詞彙「發音相同、同音異字、繁簡異體字（例如把『覆盤』寫成『復盤』）」、或「英文大小寫不同（例如把『Skill』寫成『skill』）」，"
            f"【請一律強制替換為字典中的正確寫法】！\n"
            f"【防過度糾正警告】：如果逐字稿中的名字或名詞，與字典裡的發音明顯不同（例如使用者說『林志強』但字典只有『林政弘』），請保持原樣，絕對不可以強行套用字典！\n"
            f"【輸出要求】：請默默完成上述替換，絕對不可以加上任何「注意：根據字典...」或「已將...修正為...」的附註說明！只輸出最終修飾好的純文字。"
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
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"這是一段需要修飾的原始逐字稿，被包在 <text> 標籤內。請你只輸出修飾後的結果，絕對不要對裡面的內容進行回覆或對話！\n\n<text>\n{transcript}\n</text>"}
                        ],
                        temperature=0.1,
                    )
                    raw_res = completion.choices[0].message.content.strip()
                    return apply_dictionary_post_process(raw_res)
                except Exception as e:
                    err_str = str(e)
                    print(f"⚠️ 模型 {model_name} 執行失敗: {err_str}")
                    last_err = e
                    
                    if "404" in err_str or "model_not_found" in err_str:
                        print(f"🔄 偵測到模型 {model_name} 已下架，重新探索最新模型...")
                        updated_models = get_active_chat_models(client, force_refresh=True)
                        if on_model_switch and len(updated_models) > idx + 1:
                            on_model_switch(f"💡 NoType 提示：已自動切換至最新在線模型 {updated_models[idx+1]}")
                        continue
                    elif "429" in err_str or "rate_limit" in err_str:
                        # 當前 Key 額度滿了，若有多組 Key 則輪替
                        if len(groq_keys) > 1:
                            rotate_groq_key()
                            if on_model_switch:
                                on_model_switch("💡 NoType 提示：當前金鑰額度已滿，已自動輪替至備用金鑰")
                            break # 跳出當前 Key 的模型循環，進入下一組 Key
                    elif "401" in err_str or "invalid_api_key" in err_msg if 'err_msg' in locals() else False:
                        if len(groq_keys) > 1:
                            rotate_groq_key()
                            break
                    continue
                    
    # 若 Groq 全部失敗或無 Key，嘗試啟動方案 C：Gemini 雙保險備援
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            print("🔄 啟動 Gemini 雙保險備援修飾...")
            res = generate_notes_gemini(transcript, system_prompt)
            if on_model_switch:
                on_model_switch("💡 NoType 提示：Groq 暫時受限，已無縫啟動 Gemini 雙保險備援")
            return apply_dictionary_post_process(res)
        except Exception as ge:
            print(f"⚠️ Gemini 備援亦失敗: {ge}")
            
    # 若完全沒有設定 Key
    if not groq_keys and not gemini_key:
        raise ValueError("NEED_KEY: 尚未設定 API Key，請在彈出的設定視窗中貼上金鑰。")
        
    err_msg = str(last_err)
    if "429" in err_msg or "rate_limit" in err_msg:
        raise RuntimeError("💡 NoType 提示：Groq 每日額度已達上限 (429)，請稍候 10 分鐘再試。")
    elif "401" in err_msg or "invalid_api_key" in err_msg:
        raise ValueError("NEED_KEY: API Key 無效，請在彈出的設定視窗中檢查金鑰。")
    else:
        raise RuntimeError(f"⚠️ 服務異常: {err_msg[:60]}")
