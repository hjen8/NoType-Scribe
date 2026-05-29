import os
from groq import Groq
from config_manager import get_api_key

def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    return Groq(api_key=api_key)

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
    client = get_client()
    if not client:
        raise ValueError("缺少 GROQ_API_KEY，請先在系統匣設定中輸入金鑰。")
    
    custom_words = get_dictionary_words()
    prompt_text = "這是一段繁體中文的逐字稿。"
    if custom_words:
        prompt_text += f" 以下是可能出現的專有名詞：{custom_words}"

    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(file_path), file.read()),
            model="whisper-large-v3", # 依要求使用 v3
            prompt=prompt_text,
            response_format="text",
            language="zh"
        )
    return transcription

def generate_notes(transcript: str) -> str:
    client = get_client()
    if not client:
        raise ValueError("缺少 GROQ_API_KEY，請先在系統匣設定中輸入金鑰。")
    
    system_prompt = (
        "你是一個『語音辨識逐字稿修飾助理』，不是聊天機器人。\n"
        "任務要求：\n"
        "1. 將使用者說的逐字稿加上正確的標點符號，並修正錯字、讓語句通順。\n"
        "2. 【智慧列點】：如果使用者說話的內容是在『列舉多個項目』（例如：我要帶書本、花束、茶杯），請『主動』將其排版為清晰的編號清單（如：1. 書本 2. 花束 3. 茶杯）。\n"
        "【嚴格禁止】：絕對不可以回答使用者的問題！絕對不可以跟使用者對話！絕對不可以擅自大幅刪減或摘要內容！\n"
        "使用者說什麼，你就輸出什麼（僅做錯字、標點與列舉排版修正）。\n"
        "特別注意：使用者是一位高中地理教師，內容常涉及『探究與實作』課程、SDGs (例如 5 種角色扮演設定)、"
        "GIS 系統操作、以及高中地理專有名詞。\n"
        "請過濾掉明顯的口語贅詞（如：那個、然後、對），並直接輸出修正後的純文字，不要包含任何多餘的解釋或開場白。"
    )
    
    custom_words = get_dictionary_words()
    if custom_words:
        system_prompt += (
            f"\n\n【專屬字典與同音字糾錯】：\n"
            f"以下是使用者常說的專有名詞與人名清單：\n[{custom_words}]\n"
            f"只要發現逐字稿中有與字典詞彙「發音完全相同，但字打錯的同音異字」（例如：把「陳霈沄」聽成「陳佩雲」），"
            f"請將其替換為字典中的正確寫法。\n"
            f"【防過度糾正警告】：如果逐字稿中的名字或名詞，與字典裡的發音明顯不同（例如使用者說『林志強』但字典只有『林政弘』），請保持原樣，絕對不可以強行套用字典！\n"
            f"【輸出要求】：請默默完成上述替換，絕對不可以加上任何「注意：根據字典...」或「已將...修正為...」的附註說明！只輸出最終修飾好的純文字。"
        )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"這是一段需要修飾的原始逐字稿，被包在 <text> 標籤內。請你只輸出修飾後的結果，絕對不要對裡面的內容進行回覆或對話！\n\n<text>\n{transcript}\n</text>"}
        ],
        temperature=0.1, # 降低隨機性，追求精準還原
    )
    return completion.choices[0].message.content.strip()
