/**
 * NoType Cloudflare Worker
 * 專為 iPhone iOS 捷徑與行動裝置打造的 NoType 雲端中繼 API
 * 
 * 功能：
 * 1. 接收手機錄製的音訊檔 (.m4a, .wav)
 * 2. 轉發 Groq Whisper (whisper-large-v3-turbo) 進行極速語音辨識 (< 0.5s)
 * 3. 自動動態同步 GitHub 上的 dictionary.txt (專屬自訂字典) 與 corrections.json (自癒學習庫)
 * 4. 呼叫 Groq Llama 3.3 進行臺灣繁體化、去贅字、標點符號與專屬術語校正
 * 5. 二次比對自癒學習庫精準替換
 * 6. 回傳修飾完成的純文字，iOS 捷徑可直接寫入剪貼簿！
 */

const GITHUB_DICT_URL = "https://raw.githubusercontent.com/hjen8/NoType-Scribe/main/skills/typeless-scribe/dictionary.txt";
const GITHUB_CORR_URL = "https://raw.githubusercontent.com/hjen8/NoType-Scribe/main/skills/typeless-scribe/corrections.json";

// 快取機制：避免每次請求都重複向 GitHub 發送請求 (快取 5 分鐘)
let cachedDict = null;
let cachedCorr = null;
let lastCacheTime = 0;
const CACHE_TTL_MS = 5 * 60 * 1000;

async function getDictionaryAndCorrections() {
  const now = Date.now();
  if (cachedDict && cachedCorr && (now - lastCacheTime < CACHE_TTL_MS)) {
    return { dictionary: cachedDict, corrections: cachedCorr };
  }

  try {
    const [dictRes, corrRes] = await Promise.all([
      fetch(GITHUB_DICT_URL, { headers: { "User-Agent": "NoType-Cloudflare-Worker" } }),
      fetch(GITHUB_CORR_URL, { headers: { "User-Agent": "NoType-Cloudflare-Worker" } })
    ]);

    if (dictRes.ok) {
      const dictText = await dictRes.text();
      // 解析 dictionary.txt：過濾註解 (#) 與分類標題 (===)
      cachedDict = dictText
        .split("\n")
        .map(line => line.trim())
        .filter(line => line && !line.startsWith("#") && !line.startsWith("===") && !line.startsWith("["))
        .join("、");
    } else {
      cachedDict = cachedDict || "";
    }

    if (corrRes.ok) {
      cachedCorr = await corrRes.json();
    } else {
      cachedCorr = cachedCorr || {};
    }

    lastCacheTime = now;
  } catch (err) {
    console.error("Failed to fetch dictionary/corrections from GitHub:", err);
    cachedDict = cachedDict || "";
    cachedCorr = cachedCorr || {};
  }

  return { dictionary: cachedDict, corrections: cachedCorr };
}

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);

    // 1. 健康檢查首頁
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "NoType Cloud API (Cloudflare Worker)",
        endpoints: {
          transcribe: "POST /transcribe (接收音訊並轉錄潤飾)",
          dictionary: "GET /dictionary (檢視目前同步的雲端字典)"
        },
        time: new Date().toISOString()
      }, null, 2), {
        headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" }
      });
    }

    // 2. 檢視目前已快取的字典
    if (url.pathname === "/dictionary") {
      const { dictionary, corrections } = await getDictionaryAndCorrections();
      return new Response(JSON.stringify({
        cachedWords: dictionary,
        correctionsMap: corrections,
        lastCacheTime: new Date(lastCacheTime).toISOString()
      }, null, 2), {
        headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" }
      });
    }

    // 3. 核心語音轉錄端點
    if (url.pathname === "/transcribe" && request.method === "POST") {
      const groqApiKey = env.GROQ_API_KEY;
      if (!groqApiKey) {
        return new Response("Error: 請在 Cloudflare Worker 後台設定 GROQ_API_KEY 環境變數！", { status: 500, headers: corsHeaders });
      }

      try {
        const contentType = request.headers.get("Content-Type") || "";
        let audioBlob = null;
        let fileName = "audio.m4a";

        if (contentType.includes("multipart/form-data")) {
          const formData = await request.formData();
          audioBlob = formData.get("file") || formData.get("audio");
          if (!audioBlob) {
            return new Response("Error: 找不到上傳的音訊檔案 (欄位請指定為 file)", { status: 400, headers: corsHeaders });
          }
          if (audioBlob.name) fileName = audioBlob.name;
        } else {
          // 直接傳送二進位音訊 raw body
          audioBlob = await request.blob();
        }

        // --- Step 1: 呼叫 Groq Whisper 進行 STT ---
        const whisperFormData = new FormData();
        whisperFormData.append("file", audioBlob, fileName);
        whisperFormData.append("model", "whisper-large-v3-turbo");
        whisperFormData.append("language", "zh");
        whisperFormData.append("response_format", "json");
        whisperFormData.append("prompt", "繁體中文，臺灣用語。");

        const whisperRes = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${groqApiKey}`
          },
          body: whisperFormData
        });

        if (!whisperRes.ok) {
          const errText = await whisperRes.text();
          return new Response(`Groq Whisper 辨識失敗: ${errText}`, { status: 500, headers: corsHeaders });
        }

        const whisperJson = await whisperRes.json();
        const rawText = (whisperJson.text || "").trim();

        if (!rawText) {
          return new Response("", { status: 200, headers: corsHeaders });
        }

        // --- Step 2: 獲取最新專屬字典與自癒學習庫 ---
        const { dictionary, corrections } = await getDictionaryAndCorrections();

        // --- Step 3: 呼叫 Groq Llama 3.3 進行臺灣繁體潤飾與標點斷句 ---
        const systemPrompt = `你是一個專業的語音輸入文本潤飾助理。你的任務是將語音轉錄的原始文字整理為流暢、自然的臺灣標準正體中文。
嚴格遵守以下準則：
1. 【100% 臺灣繁體中文】：嚴禁出現任何簡體字或中國大陸用語（例如：「質量」請依語意改為「品質」或保留「物理質量」、「信息」改為「資訊」、「本格拉」改為「本吉拉」）。
2. 【專屬自訂術語強制遵守】：語音轉錄若出現相關詞彙，必須嚴格匹配以下專屬字典：
${dictionary || "（目前無自訂術語）"}
3. 【自適應標點符號與斷句】：依據中文語意自然加入標點符號（，、。！？），禁止每句話都以逗號到底。
4. 【去除贅字與口語結巴】：去除「那個、嗯、啊、就是說、然後」等無意義口頭禪與結巴重複。
5. 【極致純淨輸出】：嚴禁任何多餘的問候、寒暄、引言、代碼區塊或解釋，只輸出最終潤飾後的純文字！`;

        const chatRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${groqApiKey}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            model: "llama-3.3-70b-versatile",
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: rawText }
            ],
            temperature: 0.1,
            max_tokens: 1024
          })
        });

        let polishedText = rawText;
        if (chatRes.ok) {
          const chatJson = await chatRes.json();
          if (chatJson.choices && chatJson.choices[0] && chatJson.choices[0].message) {
            polishedText = chatJson.choices[0].message.content.trim();
          }
        }

        // --- Step 4: 自癒學習庫二度精準替換 ---
        if (corrections && Object.keys(corrections).length > 0) {
          for (const [wrong, right] of Object.entries(corrections)) {
            if (wrong && right && polishedText.includes(wrong)) {
              polishedText = polishedText.replaceAll(wrong, right);
            }
          }
        }

        // 檢查客戶端要求格式 (iOS 捷徑預設接受 text/plain，可直接作為變數寫入剪貼簿)
        const acceptHeader = request.headers.get("Accept") || "";
        if (acceptHeader.includes("application/json")) {
          return new Response(JSON.stringify({ text: polishedText, raw: rawText }), {
            headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" }
          });
        }

        return new Response(polishedText, {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "text/plain; charset=utf-8" }
        });

      } catch (err) {
        return new Response(`處理異常: ${err.message}`, { status: 500, headers: corsHeaders });
      }
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  }
};
