#!/usr/bin/env python3
import sys


WINDOWS_DIALOG_TITLES = {
    "Scene(s) Have Been Modified": "save_modified_scenes_prompt",
    "Save Scene": "save_scene_dialog",
}


def detect_modal_blocker(unity_pid, scope="exec"):
    if not unity_pid or sys.platform != "win32":
        return None
    title = _detect_windows_dialog_title(unity_pid)
    if title is None:
        return None
    blocker_type = WINDOWS_DIALOG_TITLES.get(title)
    if blocker_type is None:
        return None
    return {"type": blocker_type, "scope": scope}


def _detect_windows_dialog_title(unity_pid):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
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

    gw_owner = 4
    matched_titles = []

    def callback(hwnd, _l_param):
        if not is_window_visible(hwnd):
            return True
        process_id = wintypes.DWORD()
        get_window_thread_process_id(hwnd, ctypes.byref(process_id))
        if process_id.value != unity_pid:
            return True
        if not get_window(hwnd, gw_owner):
            return True
        title_length = get_window_text_length(hwnd)
        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
        get_window_text(hwnd, title_buffer, len(title_buffer))
        title = title_buffer.value
        if title in WINDOWS_DIALOG_TITLES:
            matched_titles.append(title)
            return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    enum_windows(enum_proc, 0)
    if not matched_titles:
        return None
    return matched_titles[0]
