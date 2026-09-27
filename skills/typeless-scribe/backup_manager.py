import os
import shutil
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 優先備份目標：Dropbox Brain 專屬目錄
DROPBOX_CANDIDATES = [
    r"D:\Dropbox\Brain\NoType_Backup",
    os.path.join(os.path.expanduser("~"), "Dropbox", "Brain", "NoType_Backup"),
]

FILES_TO_BACKUP = [
    "config.json",
    "dictionary.txt",
    "corrections.json"
]

def get_backup_dir() -> str:
    """取得可用的 Dropbox 備份目錄路徑，若母目錄存在則自動建立 NoType_Backup。"""
    for candidate in DROPBOX_CANDIDATES:
        parent = os.path.dirname(candidate)
        if os.path.exists(parent):
            try:
                os.makedirs(candidate, exist_ok=True)
                return candidate
            except Exception as e:
                print(f"[Backup] 建立備份目錄失敗 ({candidate}): {e}")
    return ""

def sync_to_backup():
    """將本地的 config.json, dictionary.txt, corrections.json 靜默鏡像備份至 Dropbox。"""
    backup_dir = get_backup_dir()
    if not backup_dir:
        return False

    success_count = 0
    for filename in FILES_TO_BACKUP:
        src = os.path.join(BASE_DIR, filename)
        if os.path.exists(src):
            try:
                dst = os.path.join(backup_dir, filename)
                shutil.copy2(src, dst)
                success_count += 1
            except Exception as e:
                print(f"[Backup] 備份檔案 {filename} 失敗: {e}")

    if success_count > 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            info_file = os.path.join(backup_dir, "backup_info.txt")
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"NoType 最新鏡像備份時間: {now_str}\n")
                f.write(f"備份檔案清單: {', '.join(FILES_TO_BACKUP)}\n")
        except Exception:
            pass
        print(f"[Backup] 已於 {now_str} 自動鏡像 {success_count} 個設定/字典檔至 {backup_dir}")
        return True
    return False

def restore_from_backup():
    """若本機缺少關鍵檔案，嘗試從 Dropbox 備份目錄還原。"""
    backup_dir = get_backup_dir()
    if not backup_dir:
        return False

    restored = []
    for filename in FILES_TO_BACKUP:
        src = os.path.join(backup_dir, filename)
        dst = os.path.join(BASE_DIR, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                restored.append(filename)
            except Exception as e:
                print(f"[Backup] 還原檔案 {filename} 失敗: {e}")

    if restored:
        print(f"[Backup] 成功從雲端備份還原檔案: {', '.join(restored)}")
        return True
    return False

def sync_device_diagnostics():
    """若當前設備為筆電 (非 intel8 主機)，自動將 run_log.txt 與 history.json 鏡像至 Dropbox 供除錯診斷。"""
    try:
        import socket
        hostname = socket.gethostname().lower()
        if hostname == "intel8":
            return
        backup_dir = get_backup_dir()
        if not backup_dir:
            return
        
        # 複製 run_log.txt 到 run_log_notebook.txt
        log_src = os.path.join(BASE_DIR, "run_log.txt")
        if os.path.exists(log_src):
            try:
                shutil.copy2(log_src, os.path.join(backup_dir, "run_log_notebook.txt"))
            except Exception:
                pass
                
        # 複製 history.json 到 history_notebook.json
        hist_src = os.path.join(BASE_DIR, "history.json")
        if os.path.exists(hist_src):
            try:
                shutil.copy2(hist_src, os.path.join(backup_dir, "history_notebook.json"))
            except Exception:
                pass
    except Exception as e:
        print(f"[Backup] 診斷同步失敗: {e}")

if __name__ == "__main__":
    print(f"備份目錄: {get_backup_dir()}")
    if sync_to_backup():
        print("[OK] 鏡像備份成功！")
    else:
        print("[FAIL] 未偵測到可用備份目錄。")


