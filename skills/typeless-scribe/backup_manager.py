import os
import shutil
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 優先備份目標：Dropbox Brain 專屬目錄
DROPBOX_CANDIDATES = [
    r"D:\Dropbox\Brain\NoType_Backup",
    r"C:\Dropbox\Brain\NoType_Backup",
    os.path.join(os.path.expanduser("~"), "Dropbox", "Brain", "NoType_Backup"),
]

FILES_TO_BACKUP = [
    "config.json",
    "dictionary.txt",
    "corrections.json"
]

def get_backup_dir() -> str:
    """取得可用的 Dropbox 備份目錄路徑，優先讀取 dropbox_path.txt，若無則巡檢候選路徑。"""
    cfg_path = os.path.join(BASE_DIR, "dropbox_path.txt")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                path = f.read().strip()
                if path and os.path.exists(path):
                    return path
        except Exception:
            pass

    for candidate in DROPBOX_CANDIDATES:
        parent = os.path.dirname(candidate)
        if os.path.exists(parent):
            try:
                os.makedirs(candidate, exist_ok=True)
                return candidate
            except Exception as e:
                print(f"[Backup] 建立備份目錄失敗 ({candidate}): {e}")
    return ""


import json

def merge_corrections(corr_local: dict, corr_cloud: dict) -> tuple[dict, bool, bool]:
    """智慧合併本地與雲端 corrections.json 映射規則 (聯集保全演算法)"""
    import copy
    merged = copy.deepcopy(corr_local or {})
    changed_local = False
    changed_cloud = False
    
    for k, v in (corr_cloud or {}).items():
        if k not in merged:
            merged[k] = copy.deepcopy(v)
            changed_local = True
        elif isinstance(v, dict) and isinstance(merged[k], dict):
            for ctx_key in ['contexts', 'negative_contexts']:
                old_list = merged[k].get(ctx_key, [])
                new_list = v.get(ctx_key, [])
                combined = list(dict.fromkeys(old_list + new_list))
                if combined != old_list:
                    merged[k][ctx_key] = combined
                    changed_local = True
                if combined != new_list:
                    changed_cloud = True
                    
    for k in (corr_local or {}):
        if k not in (corr_cloud or {}):
            changed_cloud = True

    return merged, changed_local, changed_cloud


def push_to_backup(filename: str = None) -> bool:
    """本機主動修改時，立即單向鏡像推送至雲端備份（確保刪除、新增、更名秒級寫入雲端）"""
    backup_dir = get_backup_dir()
    if not backup_dir:
        return False
    targets = [filename] if filename else ["dictionary.txt", "corrections.json"]
    success = False
    for fn in targets:
        src = os.path.join(BASE_DIR, fn)
        dst = os.path.join(backup_dir, fn)
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                success = True
            except Exception as e:
                print(f"[Backup] 推送 {fn} 失敗: {e}")
    return success


def _sync_file_by_mtime(local_path: str, cloud_path: str, label: str):
    """依據檔案修改時間 (mtime) 進行精準雙向同步 (確保刪除、修改、重新命名 100% 雙向生效不復活)"""
    if os.path.exists(cloud_path) and not os.path.exists(local_path):
        shutil.copy2(cloud_path, local_path)
        print(f"[Sync] 本地缺少 {label}，已從雲端完全還原！")
        return
    if os.path.exists(local_path) and not os.path.exists(cloud_path):
        shutil.copy2(local_path, cloud_path)
        print(f"[Sync] 雲端缺少 {label}，已鏡像上傳本地檔案！")
        return
    if os.path.exists(local_path) and os.path.exists(cloud_path):
        local_mtime = os.path.getmtime(local_path)
        cloud_mtime = os.path.getmtime(cloud_path)
        
        # 門檻設為 1.0 秒
        if cloud_mtime > local_mtime + 1.0:
            shutil.copy2(cloud_path, local_path)
            print(f"[Sync] 雲端 {label} 較新，已自動拉取更新至本地！")
        elif local_mtime > cloud_mtime + 1.0:
            shutil.copy2(local_path, cloud_path)
            print(f"[Sync] 本地 {label} 較新，已自動推送更新至雲端！")


def sync_bidirectional() -> bool:
    """
    NoType 雙向時間戳精準同步核心管線 (Timestamp-Based Bidirectional Sync)：
    1. 對 dictionary.txt 與 corrections.json 比對修改時間 (mtime)：
       - 若雲端更新：從雲端拉取至本地 (Pull)
       - 若本地更新：從本地推送至雲端 (Push)
       - 徹底解決純聯集合併 (Union Merge) 導致「刪除字詞無法消除、反覆復活」的重大缺陷！
    2. 對 config.json 實施遺失自癒恢復（若本地遺失則還原，但不跨機盲目覆蓋硬體設備設定）。
    3. 同步完成後自動更新 backup_info.txt。
    """
    backup_dir = get_backup_dir()
    if not backup_dir:
        return False

    try:
        # 1. 字典 dictionary.txt 時間戳雙向同步
        local_dict = os.path.join(BASE_DIR, "dictionary.txt")
        cloud_dict = os.path.join(backup_dir, "dictionary.txt")
        _sync_file_by_mtime(local_dict, cloud_dict, "dictionary.txt")

        # 2. 自癒修正 corrections.json 時間戳雙向同步
        local_corr_path = os.path.join(BASE_DIR, "corrections.json")
        cloud_corr_path = os.path.join(backup_dir, "corrections.json")
        _sync_file_by_mtime(local_corr_path, cloud_corr_path, "corrections.json")

        # 3. 設定檔 config.json 單向遺失救援 (不盲目跨機覆蓋硬體設備參數)
        local_cfg = os.path.join(BASE_DIR, "config.json")
        cloud_cfg = os.path.join(backup_dir, "config.json")
        if os.path.exists(cloud_cfg) and not os.path.exists(local_cfg):
            shutil.copy2(cloud_cfg, local_cfg)
            print("[Sync] 本地缺少 config.json，已從雲端備份還原！")
        elif os.path.exists(local_cfg) and not os.path.exists(cloud_cfg):
            shutil.copy2(local_cfg, cloud_cfg)
            print("[Sync] 雲端缺少 config.json，已建立初次備份！")

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info_file = os.path.join(backup_dir, "backup_info.txt")
        try:
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"NoType 最新雙向同步時間: {now_str}\n")
                f.write(f"同步模式: 時間戳精準雙向同步 (dictionary.txt, corrections.json, config.json)\n")
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[Sync] 雙向同步發生異常: {e}")
        return False


def sync_to_backup():
    """向後相容：觸發雙向智慧同步"""
    return sync_bidirectional()

def restore_from_backup():
    """向後相容：觸發雙向智慧同步"""
    return sync_bidirectional()

def sync_device_diagnostics():
    """若當前設備為筆電 (非 intel8 主機)，自動將 run_log.txt、history.json 與本地 dictionary.txt 鏡像至 Dropbox 供診斷與保全。"""
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

        # 複製本地字典到 dictionary_notebook.txt 供保全
        dict_src = os.path.join(BASE_DIR, "dictionary.txt")
        if os.path.exists(dict_src):
            try:
                shutil.copy2(dict_src, os.path.join(backup_dir, "dictionary_notebook.txt"))
            except Exception:
                pass
    except Exception as e:
        print(f"[Backup] 診斷同步失敗: {e}")

if __name__ == "__main__":
    print(f"備份目錄: {get_backup_dir()}")
    if sync_bidirectional():
        print("[OK] 雙向智慧同步成功！")
    else:
        print("[FAIL] 未偵測到可用備份目錄。")


