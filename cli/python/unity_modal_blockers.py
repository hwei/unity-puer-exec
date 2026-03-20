#!/usr/bin/env python3
import sys
import time


WINDOWS_DIALOG_SPECS = {
    "Scene(s) Have Been Modified": {
        "type": "save_modified_scenes_prompt",
        "cancel_labels": ("&Cancel", "Cancel", "取消"),
    },
    "Save Scene": {
        "type": "save_scene_dialog",
        "cancel_labels": ("&Cancel", "Cancel", "取消"),
    },
}

IDCANCEL = 2
GW_OWNER = 4
BM_CLICK = 0x00F5


def detect_modal_blocker(unity_pid, scope="exec"):
    blockers = list_supported_modal_blockers(unity_pid, scope=scope)
    if not blockers:
        return None
    return blockers[0]


def list_supported_modal_blockers(unity_pid, scope="exec"):
    if not unity_pid or sys.platform != "win32":
        return []
    dialogs = _list_windows_dialogs(unity_pid)
    blockers = []
    for dialog in dialogs:
        spec = WINDOWS_DIALOG_SPECS.get(dialog["title"])
        if spec is None:
            continue
        blocker = {"type": spec["type"]}
        if scope is not None:
            blocker["scope"] = scope
        blockers.append(blocker)
    return blockers


def resolve_modal_blocker(unity_pid, action="cancel", timeout_ms=1500, poll_interval_ms=100):
    if not unity_pid or sys.platform != "win32":
        return {"ok": False, "status": "no_supported_blocker"}
    if action != "cancel":
        raise ValueError("unsupported action: {}".format(action))

    dialogs = _list_supported_windows_dialogs(unity_pid)
    if not dialogs:
        return {"ok": False, "status": "no_supported_blocker"}
    if len(dialogs) > 1:
        return {
            "ok": False,
            "status": "resolution_failed",
            "error": "multiple_supported_blockers",
        }

    dialog = dialogs[0]
    if not _click_cancel_button(dialog):
        return {
            "ok": False,
            "status": "resolution_failed",
            "action": action,
            "blocker": {"type": dialog["type"]},
            "error": "cancel_control_not_found",
        }

    deadline = time.time() + (max(timeout_ms, 1) / 1000.0)
    poll_seconds = max(poll_interval_ms, 1) / 1000.0
    while time.time() < deadline:
        if not _is_window_present(dialog["hwnd"]):
            return {
                "ok": True,
                "status": "completed",
                "result": {
                    "status": "resolved",
                    "action": action,
                    "blocker": {"type": dialog["type"]},
                },
            }
        time.sleep(poll_seconds)

    return {
        "ok": False,
        "status": "resolution_failed",
        "action": action,
        "blocker": {"type": dialog["type"]},
        "error": "click_not_confirmed",
    }


def _list_supported_windows_dialogs(unity_pid):
    dialogs = []
    for dialog in _list_windows_dialogs(unity_pid):
        spec = WINDOWS_DIALOG_SPECS.get(dialog["title"])
        if spec is None:
            continue
        dialogs.append(
            {
                "hwnd": dialog["hwnd"],
                "title": dialog["title"],
                "type": spec["type"],
                "cancel_labels": spec["cancel_labels"],
            }
        )
    return dialogs


def _list_windows_dialogs(unity_pid):
    user32, wintypes, ctypes = _load_win32_modules()

    enum_windows = user32.EnumWindows
    get_window_text_length = user32.GetWindowTextLengthW
    get_window_text = user32.GetWindowTextW
    is_window_visible = user32.IsWindowVisible
    get_window_thread_process_id = user32.GetWindowThreadProcessId
    get_window = user32.GetWindow

    enum_windows.restype = wintypes.BOOL
    enum_windows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    get_window_text_length.restype = ctypes.c_int
    get_window_text_length.argtypes = [wintypes.HWND]
    get_window_text.restype = ctypes.c_int
    get_window_text.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    is_window_visible.restype = wintypes.BOOL
    is_window_visible.argtypes = [wintypes.HWND]
    get_window_thread_process_id.restype = wintypes.DWORD
    get_window_thread_process_id.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    get_window.restype = wintypes.HWND
    get_window.argtypes = [wintypes.HWND, ctypes.c_uint]

    dialogs = []

    def callback(hwnd, _l_param):
        if not is_window_visible(hwnd):
            return True
        process_id = wintypes.DWORD()
        get_window_thread_process_id(hwnd, ctypes.byref(process_id))
        if process_id.value != unity_pid:
            return True
        if not get_window(hwnd, GW_OWNER):
            return True
        title = _get_window_text(hwnd, get_window_text_length, get_window_text, ctypes)
        if title:
            dialogs.append({"hwnd": hwnd, "title": title})
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    enum_windows(enum_proc, 0)
    return dialogs


def _click_cancel_button(dialog):
    cancel_hwnd = _find_cancel_button(dialog["hwnd"], dialog["cancel_labels"])
    if not cancel_hwnd:
        return False
    user32, wintypes, ctypes = _load_win32_modules()
    send_message = user32.SendMessageW
    send_message.restype = wintypes.LPARAM
    send_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    send_message(cancel_hwnd, BM_CLICK, 0, 0)
    return True


def _find_cancel_button(dialog_hwnd, cancel_labels):
    user32, wintypes, ctypes = _load_win32_modules()
    enum_child_windows = user32.EnumChildWindows
    get_class_name = user32.GetClassNameW
    get_window_text_length = user32.GetWindowTextLengthW
    get_window_text = user32.GetWindowTextW
    get_dlg_ctrl_id = user32.GetDlgCtrlID

    enum_child_windows.restype = wintypes.BOOL
    enum_child_windows.argtypes = [
        wintypes.HWND,
        ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
        wintypes.LPARAM,
    ]
    get_class_name.restype = ctypes.c_int
    get_class_name.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    get_window_text_length.restype = ctypes.c_int
    get_window_text_length.argtypes = [wintypes.HWND]
    get_window_text.restype = ctypes.c_int
    get_window_text.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    get_dlg_ctrl_id.restype = ctypes.c_int
    get_dlg_ctrl_id.argtypes = [wintypes.HWND]

    matched_hwnd = [None]
    label_set = set(cancel_labels)

    def callback(hwnd, _l_param):
        class_name = _get_window_text(hwnd, None, get_class_name, ctypes, buffer_size=256)
        if class_name != "Button":
            return True
        ctrl_id = get_dlg_ctrl_id(hwnd)
        if ctrl_id == IDCANCEL:
            matched_hwnd[0] = hwnd
            return False
        text = _get_window_text(hwnd, get_window_text_length, get_window_text, ctypes)
        if text in label_set:
            matched_hwnd[0] = hwnd
            return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    enum_child_windows(dialog_hwnd, enum_proc, 0)
    return matched_hwnd[0]


def _is_window_present(hwnd):
    user32, wintypes, _ctypes = _load_win32_modules()
    is_window = user32.IsWindow
    is_window_visible = user32.IsWindowVisible
    is_window.restype = wintypes.BOOL
    is_window.argtypes = [wintypes.HWND]
    is_window_visible.restype = wintypes.BOOL
    is_window_visible.argtypes = [wintypes.HWND]
    return bool(is_window(hwnd) and is_window_visible(hwnd))


def _get_window_text(hwnd, get_window_text_length, get_text_fn, ctypes, buffer_size=None):
    if buffer_size is None:
        title_length = get_window_text_length(hwnd)
        buffer_size = title_length + 1
    title_buffer = ctypes.create_unicode_buffer(buffer_size)
    get_text_fn(hwnd, title_buffer, len(title_buffer))
    return title_buffer.value


def _load_win32_modules():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    return user32, wintypes, ctypes
