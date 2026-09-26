"""
screen_context.py - 前景視窗語境探測與熱詞萃取模組
支援 Win32 UI Automation 與視窗標題探測，提供環境語境 (Ambient Context) 給陣營 B 子句消歧義
"""
import ctypes
import re
import time

def get_foreground_window_text(hwnd=None, max_chars=800, timeout_sec=0.08) -> str:
    """
    從前景視窗中探測最後可見文字 (Visible Text)：
    - 優先使用 Win32 UI Automation 探測焦點視窗或文字容器
    - 嚴格設定超時保護 (0.08s)，若逾時或出錯立即回退，絕不阻塞錄音主流程
    """
    if not hwnd:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return ""
        
    collected = []
    
    # 1. 先抓取視窗標題 (0ms，極速且穩定)
    user32 = ctypes.windll.user32
    title_buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title_buf, 512)
    title = title_buf.value.strip()
    if title:
        collected.append(title)
        
    # 2. 使用 UI Automation 探測控制項中的可見文字
    try:
        import uiautomation as auto
        t0 = time.time()
        
        # 取得目標視窗控制項
        win_ctrl = auto.ControlFromHandle(hwnd)
        if win_ctrl:
            # 優先嘗試取得當前焦點控制項 (Focused Control)
            try:
                focused = auto.GetFocusedControl()
                if focused:
                    f_name = focused.Name or ""
                    if f_name.strip() and f_name.strip() not in collected:
                        collected.append(f_name.strip())
                    # 嘗試取得 ValuePattern
                    vp = focused.GetValuePattern()
                    if vp and vp.Value and vp.Value not in collected:
                        collected.append(vp.Value.strip())
            except Exception:
                pass
            
            # 遍歷視窗中的文字容器
            nodes_checked = 0
            stack = [win_ctrl]
            while stack and (time.time() - t0) < timeout_sec and sum(len(s) for s in collected) < max_chars:
                curr = stack.pop()
                nodes_checked += 1
                if nodes_checked > 60:
                    break
                    
                try:
                    val = curr.Name or ""
                    if len(val.strip()) > 1 and val.strip() not in collected:
                        collected.append(val.strip())
                        
                    if curr.ControlTypeName in ("EditControl", "DocumentControl"):
                        try:
                            vp = curr.GetValuePattern()
                            if vp and vp.Value and vp.Value not in collected:
                                collected.append(vp.Value.strip())
                        except Exception:
                            pass
                            
                    children = curr.GetChildren()
                    if len(children) > 15:
                        children = children[-15:]
                    for ch in reversed(children):
                        stack.append(ch)
                except Exception:
                    continue
                    
    except Exception as e:
        pass
        
    combined = " ".join(collected)
    if len(combined) > max_chars:
        combined = combined[-max_chars:]
    return combined

def extract_ambient_keywords(text: str, max_words=20) -> list:
    """
    從畫面文字中萃取出有語意價值的熱詞：
    - 抓取中文 2~6 字詞彙、名詞與關鍵概念
    """
    if not text:
        return []
        
    raw_words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    stopwords = {
        "這個", "那個", "什麼", "如何", "可以", "我們", "你們", "他們", 
        "因為", "所以", "如果", "但是", "而且", "雖然", "這裡", "那裡",
        "一個", "沒有", "不是", "就是", "還是", "或者", "以及", "有關"
    }
    
    seen = set()
    keywords = []
    for w in reversed(raw_words):
        if w not in seen and w not in stopwords:
            seen.add(w)
            keywords.append(w)
            if len(keywords) >= max_words:
                break
                
    return keywords
