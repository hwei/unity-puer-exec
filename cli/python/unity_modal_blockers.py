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
    "Enter Safe Mode?": {
        "type": "safe_mode_dialog",
        "cancel_labels": ("&Enter Safe Mode", "Enter Safe Mode"),
        "click_method": "keyboard",
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
    # Also check Unity main window title for SAFE MODE state (after dialog dismissed)
    main_title = _get_unity_main_window_title(unity_pid)
    if main_title and "SAFE MODE" in main_title.upper():
        # Avoid duplicate if already detected via dialog
        if not any(b["type"] == "safe_mode_dialog" for b in blockers):
            blockers.append({"type": "safe_mode_dialog", "scope": scope})
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





def _foreground_unity_window(unity_pid):
    """Bring the main Unity window to foreground."""
    if not unity_pid or sys.platform != "win32":
        return
    user32, wintypes, ctypes = _load_win32_modules()
    found = [None]

    def callback(hwnd, _l_param):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value != unity_pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if title and ("Unity" in title or "SAFE MODE" in title.upper()):
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 200 and h > 200:
                    found[0] = hwnd
                    return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    user32.EnumWindows(enum_proc, 0)
    if found[0]:
        user32.SetForegroundWindow(found[0])

def _get_unity_main_window_title(unity_pid):
    """Return the main Unity window title for the given PID, or None."""
    user32, wintypes, ctypes = _load_win32_modules()
    result = [None]

    def callback(hwnd, _l_param):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value != unity_pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        # Main Unity window has a large size and a title containing "Unity"
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if title and ("Unity" in title or "SAFE MODE" in title.upper()):
            # Check it is a main window (has size > 100x100)
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 200 and h > 200:
                    result[0] = title
                    return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    user32.EnumWindows(enum_proc, 0)
    return result[0]

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
        # Note: some dialogs (e.g. Safe Mode) appear before the main window and have no owner
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
    click_method = dialog.get("click_method", "bm_click")
    if click_method == "mouse_event":
        return _click_via_mouse_event(cancel_hwnd)
    if click_method == "keyboard":
        return _click_via_keyboard(dialog["hwnd"])
    user32, wintypes, ctypes = _load_win32_modules()
    send_message = user32.SendMessageW
    send_message.restype = wintypes.LPARAM
    send_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    send_message(cancel_hwnd, BM_CLICK, 0, 0)
    return True


def _click_via_mouse_event(hwnd):
    """Click a button using hardware-level mouse_event (for custom UI that ignores BM_CLICK)."""
    user32, wintypes, ctypes = _load_win32_modules()
    get_window_rect = user32.GetWindowRect
    get_window_rect.restype = wintypes.BOOL
    get_window_rect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    set_cursor_pos = user32.SetCursorPos
    set_cursor_pos.restype = wintypes.BOOL
    set_cursor_pos.argtypes = [ctypes.c_int, ctypes.c_int]
    mouse_event = user32.mouse_event
    mouse_event.restype = None
    mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]

    rect = wintypes.RECT()
    if not get_window_rect(hwnd, ctypes.byref(rect)):
        return False
    x = (rect.left + rect.right) // 2
    y = (rect.top + rect.bottom) // 2
    set_cursor_pos(x, y)
    import time
    time.sleep(0.1)
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True


def _click_via_keyboard(dialog_hwnd):
    """Dismiss a dialog by sending Enter key to activate the default button."""
    user32, wintypes, ctypes = _load_win32_modules()
    set_foreground = user32.SetForegroundWindow
    set_foreground.restype = wintypes.BOOL
    set_foreground.argtypes = [wintypes.HWND]
    keybd_event = user32.keybd_event
    keybd_event.restype = None
    keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, wintypes.DWORD]
    # Bring dialog to foreground so it receives keyboard input
    set_foreground(dialog_hwnd)
    import time
    time.sleep(0.15)
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002
    keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.05)
    keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
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
        text = _get_window_text(hwnd, get_window_text_length, get_window_text, ctypes)
        if text in label_set:
            matched_hwnd[0] = hwnd
            return False
        ctrl_id = get_dlg_ctrl_id(hwnd)
        if ctrl_id == IDCANCEL:
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
