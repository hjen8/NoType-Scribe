import sys
import ctypes
from ctypes import wintypes
import threading
import time
import os

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            safe_args = [
                str(arg).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
                for arg in args
            ]
            print(*safe_args, **kwargs)
        except Exception:
            pass
    except Exception:
        pass

# Win32 Constants
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_POWERBROADCAST = 0x0218
WM_DEVICECHANGE = 0x0219

# Power Broadcast wParam Codes
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMECRITICAL = 0x0006
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_POWERSETTINGCHANGE = 0x8013

# Device Change wParam Codes
DBT_DEVNODES_CHANGED = 0x0007
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004

DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
WS_POPUP = 0x80000000

# 64-bit compatible WNDPROC definition
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int64,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_uint64,
    ctypes.c_int64
)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
        ("hIconSm", ctypes.c_void_p),
    ]

# Setup Win32 API functions with strict 64-bit argtypes and restypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.UnregisterClassW.argtypes = [ctypes.c_wchar_p, wintypes.HINSTANCE]
user32.UnregisterClassW.restype = wintypes.BOOL

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, ctypes.c_wchar_p, ctypes.c_wchar_p,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_int64

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_int64
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

has_suspend_notify = hasattr(user32, 'RegisterSuspendResumeNotification')
if has_suspend_notify:
    user32.RegisterSuspendResumeNotification.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    user32.RegisterSuspendResumeNotification.restype = wintypes.HANDLE
    user32.UnregisterSuspendResumeNotification.argtypes = [wintypes.HANDLE]
    user32.UnregisterSuspendResumeNotification.restype = wintypes.BOOL


class PowerMonitor:
    """
    Win32 原生頂層隱藏視窗電源與硬體事件監聽器。
    精準攔截 Windows 系統休眠喚醒 (WM_POWERBROADCAST: PBT_APMRESUME...) 
    以及音訊裝置插拔 (WM_DEVICECHANGE)，自動調度音訊引擎重置與重連。
    """
    def __init__(self, on_resume=None, debounce_delay=0.8):
        self.on_resume = on_resume
        self.debounce_delay = debounce_delay
        self.thread = None
        self.hwnd = None
        self.hinstance = None
        self.class_name = f"NoType_PowerMonitor_{os.getpid()}"
        self.h_power_notify = None
        self._wndproc_ref = None  # 防止 ctypes callback 被 GC 資源回收
        self._debounce_timer = None
        self._lock = threading.Lock()
        self._ready_event = threading.Event()
        self._running = False

    def _trigger_resume_debounced(self, reason: str):
        """防抖延遲觸發：等待 Windows 核心驅動端點就緒後執行回呼"""
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            
            def _worker():
                safe_print(f"[PowerMonitor] Debounce elapsed ({self.debounce_delay}s). Executing resume callback for reason: {reason}")
                if self.on_resume:
                    try:
                        self.on_resume(reason)
                    except Exception as e:
                        safe_print(f"[PowerMonitor] Error in on_resume callback: {e}")

            self._debounce_timer = threading.Timer(self.debounce_delay, _worker)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_POWERBROADCAST:
                if wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND, PBT_APMRESUMECRITICAL):
                    reason_desc = (
                        "ResumeAutomatic" if wparam == PBT_APMRESUMEAUTOMATIC 
                        else "ResumeSuspend" if wparam == PBT_APMRESUMESUSPEND 
                        else "ResumeCritical"
                    )
                    safe_print(f"[PowerMonitor] ⚡ System Wake-up detected ({reason_desc}, wParam={hex(wparam)})")
                    self._trigger_resume_debounced(f"System Wake-up ({reason_desc})")
                    return 1

            elif msg == WM_DEVICECHANGE:
                if wparam in (DBT_DEVNODES_CHANGED, DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
                    event_desc = (
                        "DevNodesChanged" if wparam == DBT_DEVNODES_CHANGED
                        else "DeviceArrival" if wparam == DBT_DEVICEARRIVAL
                        else "DeviceRemove"
                    )
                    # 僅在除錯時記錄，裝置節點可能頻繁變動，透過 debounce 匯流
                    self._trigger_resume_debounced(f"Audio/Device Change ({event_desc})")
                    return 1

            elif msg == WM_DESTROY:
                if self.h_power_notify and has_suspend_notify:
                    try:
                        user32.UnregisterSuspendResumeNotification(self.h_power_notify)
                    except Exception:
                        pass
                    self.h_power_notify = None
                user32.PostQuitMessage(0)
                return 0

        except Exception as e:
            safe_print(f"[PowerMonitor] Exception in WNDPROC: {e}")

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _run_loop(self):
        try:
            self.hinstance = kernel32.GetModuleHandleW(None)
            self._wndproc_ref = WNDPROC(self._wnd_proc)

            wndclass = WNDCLASSEXW()
            wndclass.cbSize = ctypes.sizeof(WNDCLASSEXW)
            wndclass.style = 0
            wndclass.lpfnWndProc = self._wndproc_ref
            wndclass.hInstance = self.hinstance
            wndclass.lpszClassName = self.class_name

            atom = user32.RegisterClassExW(ctypes.byref(wndclass))
            if not atom:
                safe_print(f"[PowerMonitor] RegisterClassExW failed! LastError: {kernel32.GetLastError()}")
                self._ready_event.set()
                return

            # 建立頂層隱藏視窗 (WS_POPUP，無父視窗，專責接收系統廣播)
            self.hwnd = user32.CreateWindowExW(
                0, self.class_name, "NoTypePowerWindow",
                WS_POPUP, 0, 0, 0, 0,
                None, None, self.hinstance, None
            )

            if not self.hwnd:
                safe_print(f"[PowerMonitor] CreateWindowExW failed! LastError: {kernel32.GetLastError()}")
                user32.UnregisterClassW(self.class_name, self.hinstance)
                self._ready_event.set()
                return

            # 註冊 Windows 10/11 Modern Standby (InstantGo) 與 S3 休眠喚醒廣播
            if has_suspend_notify:
                self.h_power_notify = user32.RegisterSuspendResumeNotification(self.hwnd, DEVICE_NOTIFY_WINDOW_HANDLE)
                safe_print(f"[PowerMonitor] Registered Suspend/Resume notification: handle={self.h_power_notify}")

            self._running = True
            safe_print(f"[PowerMonitor] Top-level power broadcast listener initialized (HWND={self.hwnd}).")
            self._ready_event.set()

            # Win32 標準訊息汲取迴圈 (Message Pump)
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        except Exception as e:
            safe_print(f"[PowerMonitor] Error in message loop: {e}")
        finally:
            self._running = False
            if self.hwnd:
                try:
                    user32.DestroyWindow(self.hwnd)
                except Exception:
                    pass
                self.hwnd = None
            if self.hinstance:
                try:
                    user32.UnregisterClassW(self.class_name, self.hinstance)
                except Exception:
                    pass
            safe_print("[PowerMonitor] Message pump cleanly stopped.")

    def start(self):
        """啟動背景監聽執行緒"""
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="PowerMonitorThread")
        self.thread.start()
        self._ready_event.wait(timeout=3.0)

    def stop(self):
        """停止背景監聽並釋放 Win32 資源"""
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_DESTROY, 0, 0)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
