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


def sync_bidirectional() -> bool:
    """
    NoType 雙向智慧同步核心管線 (Smart Bidirectional Sync)：
    1. 對 dictionary.txt 實施階層式智慧合併 (merge_hierarchies)，雙機新增詞彙 100% 聯集保全，絕不互相覆蓋抹除！
    2. 對 corrections.json 實施映射規則智慧合併，筆電與桌機學習的同音錯字雙向共享。
    3. 對 config.json 實施遺失自癒恢復（若本地遺失則還原，但不跨機盲目覆蓋硬體設備設定）。
    4. 同步完成後自動更新雙端檔案與 backup_info.txt。
    """
    backup_dir = get_backup_dir()
    if not backup_dir:
        return False

    try:
        import dictionary_manager
        
        # 1. 字典 dictionary.txt 智慧合併同步
        local_dict = os.path.join(BASE_DIR, "dictionary.txt")
        cloud_dict = os.path.join(backup_dir, "dictionary.txt")
        
        if os.path.exists(cloud_dict) and not os.path.exists(local_dict):
            shutil.copy2(cloud_dict, local_dict)
            print("[Sync] 本地缺少字典，已從雲端完全還原！")
        elif os.path.exists(local_dict) and not os.path.exists(cloud_dict):
            shutil.copy2(local_dict, cloud_dict)
            print("[Sync] 雲端缺少字典，已鏡像上傳本地字典！")
        elif os.path.exists(local_dict) and os.path.exists(cloud_dict):
            h_local = dictionary_manager.load_hierarchy_from_file(local_dict)
            h_cloud = dictionary_manager.load_hierarchy_from_file(cloud_dict)
            
            merged_h, local_changed = dictionary_manager.merge_hierarchies(h_local, h_cloud)
            _, cloud_changed = dictionary_manager.merge_hierarchies(h_cloud, h_local)
            
            if local_changed:
                dictionary_manager.save_hierarchy_to_file(merged_h, local_dict)
                print(f"[Sync] 智慧合併雲端詞彙至本地字典 ({len(dictionary_manager.load_words())} 詞)！")
            if cloud_changed or local_changed:
                dictionary_manager.save_hierarchy_to_file(merged_h, cloud_dict)
                print(f"[Sync] 智慧同步合併字典至 Dropbox ({len(merged_h)} 分類)！")

        # 2. 自癒修正 corrections.json 智慧合併同步
        local_corr_path = os.path.join(BASE_DIR, "corrections.json")
        cloud_corr_path = os.path.join(backup_dir, "corrections.json")
        
        if os.path.exists(cloud_corr_path) and not os.path.exists(local_corr_path):
            shutil.copy2(cloud_corr_path, local_corr_path)
            print("[Sync] 本地缺少自癒修正檔，已從雲端完全還原！")
        elif os.path.exists(local_corr_path) and not os.path.exists(cloud_corr_path):
            shutil.copy2(local_corr_path, cloud_corr_path)
            print("[Sync] 雲端缺少自癒修正檔，已鏡像上傳本地檔案！")
        elif os.path.exists(local_corr_path) and os.path.exists(cloud_corr_path):
            try:
                with open(local_corr_path, "r", encoding="utf-8") as f:
                    local_c = json.load(f)
            except Exception:
                local_c = {}
            try:
                with open(cloud_corr_path, "r", encoding="utf-8") as f:
                    cloud_c = json.load(f)
            except Exception:
                cloud_c = {}
                
            merged_c, l_chg, c_chg = merge_corrections(local_c, cloud_c)
            if l_chg:
                with open(local_corr_path, "w", encoding="utf-8") as f:
                    json.dump(merged_c, f, ensure_ascii=False, indent=4)
                print(f"[Sync] 已合併雲端修正規則至本地 ({len(merged_c)} 條)！")
            if c_chg or l_chg:
                with open(cloud_corr_path, "w", encoding="utf-8") as f:
                    json.dump(merged_c, f, ensure_ascii=False, indent=4)
                print(f"[Sync] 已同步合併修正規則至 Dropbox ({len(merged_c)} 條)！")

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
                f.write(f"同步項目: dictionary.txt (智慧合併), corrections.json (智慧合併), config.json (遺失救援)\n")
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


