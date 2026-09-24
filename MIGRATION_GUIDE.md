# 🚀 NoType 跨設備遷移與電腦重灌災難復原指南 (Migration & Disaster Recovery Guide)

本指南專為 NoType 使用者設計，無論是**「更換新筆電」**或**「電腦當機整台重灌」**，均可在 3 分鐘內無腦滿血復原！

---

## 🛡️ 雙軌雲端安全架構（為什麼您的資料絕不會丟失？）

NoType 採用現代高可用性雙軌備份架構，將「開源程式碼」與「個人私密設定」安全解耦：

1. **第一軌：程式碼與專屬字典（GitHub 雲端）**
   - 倉庫網址：`https://github.com/hjen8/NoType-Scribe`
   - 內容物：所有 Python 程式碼、最新 342 筆專業詞庫（`dictionary.txt`）、糾錯映射表（`corrections.json`）。
   - 保障：無論本機硬碟如何損壞，程式與字典在 GitHub 永久完好。

2. **第二軌：API 金鑰與個人設定鏡像（Dropbox 雲端）**
   - 備份路徑：`D:\Dropbox\Brain\NoType_Backup\`
   - 內容物：`config.json`（含 Groq/Gemini API Key）、最新字典與糾錯備份。
   - 保障：每次 NoType 啟動或編輯字典時，系統全自動「靜默鏡像備份」至 Dropbox。即使 GitHub 不放金鑰，Dropbox 雲端永遠有您的金鑰存檔。

---

## ⚡ 三步驟極速復原 / 遷移新電腦流程

當您拿到全新筆電，或電腦重灌完成後，只需依照以下 3 步驟：

### 步驟 1：安裝 Python（只需 1 分鐘）
1. 前往 Python 官網下載安裝檔：[https://www.python.org/downloads/](https://www.python.org/downloads/)（建議 Python 3.10、3.11 或 3.12）。
2. ⚠️ **【最關鍵一步】**：執行安裝程式時，**務必勾選最下方的 `Add Python to PATH`（將 Python 加入環境變數）**，接著點擊「Install Now」。

### 步驟 2：取得 NoType 專案資料夾
您可以自由選擇以下任一種方式取得程式：
- **方式 A（隨身碟複製）**：直接將舊電腦的 `NoType` 資料夾複製到新電腦（例如放在 `E:\AI_Work\NoType` 或 `C:\NoType` 均可）。
- **方式 B（GitHub 下載）**：
  - 若有裝 Git：在終端機輸入 `git clone https://github.com/hjen8/NoType-Scribe.git NoType`
  - 若沒裝 Git：直接開啟 GitHub 網頁，點擊綠色 `Code` ➔ `Download ZIP`，解壓縮到任意目錄。

### 步驟 3：雙擊執行 `setup_new_pc.bat`（全自動一鍵完成）
1. 進入 `NoType` 根目錄，**滑鼠雙擊執行 [`setup_new_pc.bat`](setup_new_pc.bat)**。
2. 腳本將會全自動執行：
   - [1/5] 自動檢測 Python 環境。
   - [2/5] 自動建立乾淨的虛擬環境 (`venv`)。
   - [3/5] 自動安裝所有必要套件（`sounddevice`, `groq`, `pynput`, `pyautogui` 等）。
   - [4/5] 自動偵測 Dropbox 備份目錄，**無縫還原您的 `config.json`（API Key）與最新字典**。
   - [5/5] 自動在您的 Windows 桌面上建立 **「NoType 語音輸入」** 捷徑。
3. 腳本詢問是否立即啟動，按下 Enter，NoType 立即在背景啟動（系統匣出現藍色圓形圖示）！

---

## ❓ 常見問題與備援指南 (FAQ)

### Q1：新筆電沒有 D 槽（Dropbox 裝在 C 槽）怎麼辦？
`backup_manager.py` 與 `setup_new_pc.bat` 已內建智慧路徑探測：
系統會優先檢查 `D:\Dropbox\Brain\NoType_Backup`；若無 D 槽，會自動搜尋使用者個人目錄下的 `C:\Users\<您的使用者名稱>\Dropbox\Brain\NoType_Backup`。只要新電腦登入 Dropbox，就能自動對接還原！

### Q2：如果新電腦完全沒有 Dropbox，我要怎麼設定？
如果在新電腦暫時未安裝 Dropbox，執行 `setup_new_pc.bat` 時會自動為您生成一個預設的 `config.json` 模板。您只需用記事本打開 `skills\typeless-scribe\config.json`，把您的 Groq API Key 貼在引號內儲存即可：
```json
{
    "GROQ_API_KEY": "gsk_您的金鑰"
}
```

### Q3：如何確認目前是否有在正常自動備份？
您可以隨時查看 `D:\Dropbox\Brain\NoType_Backup\backup_info.txt`，裡面會記錄最後一次自動鏡像備份的精確時間戳記。
