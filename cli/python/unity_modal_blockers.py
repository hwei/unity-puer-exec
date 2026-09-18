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

# Unity ScriptUpdater consent dialog. Its title varies by Editor version
# (`API Updating` / `API Updater` / `Unity`), so it is matched by the distinctive
# sentence in its message body instead. The default button is Yes, which rewrites
# project sources, so it is auto-declined (No) with BM_CLICK and never with Enter.
API_UPDATER_DIALOG_TYPE = "api_updater_dialog"
API_UPDATER_MESSAGE_FINGERPRINT = "Some of this project's source files refer to API that has changed"
API_UPDATER_MESSAGE_FINGERPRINTS = (
    "Some of this project's source files refer to API that has changed",
    "Some of this projects source files refer to API that has changed",
    "source files refer to API that has changed",
)


def is_api_updater_message(body):
    if not body:
        return False
    return any(fingerprint in body for fingerprint in API_UPDATER_MESSAGE_FINGERPRINTS)


WINDOWS_BODY_DIALOG_SPECS = (
    {
        "type": API_UPDATER_DIALOG_TYPE,
        "message_fingerprint": API_UPDATER_MESSAGE_FINGERPRINT,
        "message_fingerprints": API_UPDATER_MESSAGE_FINGERPRINTS,
        "cancel_labels": ("&No", "No", "否"),
        "click_method": "bm_click",
    },
)

# Bounded window for the repeated No-click loop used while a command is waiting.
DEFAULT_API_UPDATER_DISMISS_TIMEOUT_MS = 2000
DEFAULT_API_UPDATER_DISMISS_POLL_MS = 100

IDCANCEL = 2
GW_OWNER = 4
GWL_STYLE = -16
BM_CLICK = 0x00F5
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
BN_CLICKED = 0
VK_RETURN = 0x0D

WS_DISABLED = 0x08000000
WS_POPUP = 0x80000000
# Modal prompts are small; Editor panels are not. Used only to sanity-check an
# ownerless window that already looks like a dialog by style.
MAX_MODAL_DIALOG_EDGE_PX = 900

# Button low-word styles that are not clickable as an action. Win32 reports
# these under the same "Button" class as push buttons, so they must be filtered
# by style rather than by class name.
NON_CLICKABLE_BUTTON_STYLES = frozenset(
    (0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0009)
)


def detect_modal_blocker(unity_pid, scope="exec"):
    blockers = list_supported_modal_blockers(unity_pid, scope=scope)
    if not blockers:
        return None
    return blockers[0]


UNKNOWN_DIALOG_TYPE = "unknown_modal_dialog"

# Unknown dialogs sort ahead of catalog dialogs: the unknown one is the likelier
# true stall, and catalog save-scene types are reachable on their own path.
BLOCKER_TYPE_ORDER = (UNKNOWN_DIALOG_TYPE, "safe_mode_dialog", "save_modified_scenes_prompt", "save_scene_dialog")


def _blocker_sort_key(blocker):
    try:
        return BLOCKER_TYPE_ORDER.index(blocker["type"])
    except ValueError:
        return len(BLOCKER_TYPE_ORDER)


def list_supported_modal_blockers(unity_pid, scope="exec"):
    if not unity_pid or sys.platform != "win32":
        return []
    dialogs = _list_windows_dialogs(unity_pid)
    blockers = []
    for dialog in dialogs:
        spec = _match_dialog_spec(dialog)
        if spec is not None and spec["type"] == API_UPDATER_DIALOG_TYPE:
            # The ScriptUpdater consent dialog is auto-recovered, never surfaced
            # to an agent as a modal blocker.
            continue
        if spec is None:
            # Outside the catalog: report it only if it actually blocks. A
            # non-blocking Editor window is skipped rather than dropped, and an
            # unrecognized modal is surfaced instead of being discarded.
            if not _is_modal_window(dialog["hwnd"]):
                continue
            blocker = _unknown_blocker_entry(dialog)
        else:
            # A catalog title hit keeps reporting without modal discrimination:
            # title is the existing contract, and adding a modality gate could
            # stop reporting dialogs reported today.
            blocker = {"type": spec["type"], "hwnd": dialog["hwnd"], "title": dialog["title"]}
            blocker.update(_button_fields(dialog["hwnd"]))
        if scope is not None:
            blocker["scope"] = scope
        blockers.append(blocker)
    # Also check Unity main window title for SAFE MODE state (after dialog dismissed)
    main_title = _get_unity_main_window_title(unity_pid)
    if main_title and "SAFE MODE" in main_title.upper():
        # Avoid duplicate if already detected via dialog
        if not any(b["type"] == "safe_mode_dialog" for b in blockers):
            # Title-only detection has no dialog to click; hwnd is omitted.
            blockers.append({"type": "safe_mode_dialog", "scope": scope})
    blockers.sort(key=_blocker_sort_key)
    return blockers


def _button_fields(dialog_hwnd):
    """``buttons`` detail for a payload, or {} when nothing is enumerable."""
    try:
        buttons = _enumerate_buttons(dialog_hwnd)
    except Exception:
        return {}
    if not buttons:
        return {}
    return {
        "buttons": [
            {"hwnd": b["hwnd"], "label": b["label"], "ctrl_id": b["ctrl_id"]}
            for b in buttons
        ]
    }


def _unknown_blocker_entry(dialog):
    entry = {
        "type": UNKNOWN_DIALOG_TYPE,
        "hwnd": dialog["hwnd"],
        "title": dialog["title"],
        "body": dialog.get("body") or "",
    }
    entry.update(_button_fields(dialog["hwnd"]))
    return entry


SAFE_MODE_TYPE = "safe_mode_dialog"


def resolve_modal_blocker(
    unity_pid,
    action="cancel",
    timeout_ms=1500,
    poll_interval_ms=100,
    hwnd=None,
    button=None,
):
    """Resolve one reported modal blocker.

    ``cancel`` is legal only for the Safe Mode dialog, where it preserves the
    existing "cancel == Enter Safe Mode" semantics. Every other reported dialog
    is resolved with ``click`` against a named window and button.
    """
    if not unity_pid or sys.platform != "win32":
        return {"ok": False, "status": "no_supported_blocker"}
    if action == "click":
        return _resolve_by_click(unity_pid, hwnd, button, timeout_ms, poll_interval_ms)
    if action != "cancel":
        raise ValueError("unsupported action: {}".format(action))
    if hwnd is not None or button is not None:
        # --hwnd/--button belong to click; silently ignoring them would resolve
        # a different dialog than the caller named.
        return {
            "ok": False,
            "status": "resolution_failed",
            "error": "action_not_supported_for_blocker",
        }

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
    if dialog["type"] != SAFE_MODE_TYPE:
        # Save-scene dialogs lost automatic cancel: dismissing them that way can
        # discard unsaved scene work, so it must be an explicit click instead.
        return {
            "ok": False,
            "status": "resolution_failed",
            "action": action,
            "blocker": {"type": dialog["type"]},
            "error": "action_not_supported_for_blocker",
        }
    if not _click_cancel_button(dialog):
        return {
            "ok": False,
            "status": "resolution_failed",
            "action": action,
            "blocker": {"type": dialog["type"]},
            "error": "cancel_control_not_found",
        }

    return _confirm_disappearance(
        dialog, action, timeout_ms=timeout_ms, poll_interval_ms=poll_interval_ms
    )


def _resolve_by_click(unity_pid, hwnd, button, timeout_ms, poll_interval_ms):
    """Activate a named button on a validated window."""
    if hwnd is None or not button:
        return {
            "ok": False,
            "status": "resolution_failed",
            "error": "button_not_found",
        }
    blocker = _find_blocker_by_hwnd(unity_pid, hwnd)
    if blocker is None:
        # Stale handle, or a window belonging to another process: never drive a
        # click against a window we cannot confirm is the target dialog.
        return {
            "ok": False,
            "status": "resolution_failed",
            "error": "window_not_found",
        }
    buttons = _enumerate_buttons(hwnd)
    target = _match_button(buttons, button)
    if target is None:
        return {
            "ok": False,
            "status": "resolution_failed",
            "action": "click",
            "blocker": {"type": blocker["type"]},
            "error": "button_not_found",
        }

    if blocker["type"] == SAFE_MODE_TYPE:
        # Safe Mode ignores message-level clicks historically; keep the
        # foreground keyboard path for it.
        _click_via_keyboard(hwnd)
    else:
        _click_button(hwnd, target)

    return _confirm_disappearance(
        blocker,
        "click",
        hwnd=hwnd,
        timeout_ms=timeout_ms,
        poll_interval_ms=poll_interval_ms,
    )


def _find_blocker_by_hwnd(unity_pid, hwnd):
    """The reported blocker matching ``hwnd``, or None when it is not one.

    Re-validates ownership against the project's Editor pid so a stale or
    foreign handle cannot drive a click.
    """
    for blocker in list_supported_modal_blockers(unity_pid, scope=None):
        if blocker.get("hwnd") == hwnd:
            return blocker
    return None


def _confirm_disappearance(blocker, action, hwnd=None, timeout_ms=1500, poll_interval_ms=100):
    """Poll until the dialog closes, then report the resolution result."""
    target_hwnd = hwnd if hwnd is not None else blocker["hwnd"]
    deadline = time.time() + (max(timeout_ms, 1) / 1000.0)
    poll_seconds = max(poll_interval_ms, 1) / 1000.0
    while time.time() < deadline:
        if not _is_window_present(target_hwnd):
            return {
                "ok": True,
                "status": "completed",
                "result": {
                    "status": "resolved",
                    "action": action,
                    "blocker": {"type": blocker["type"]},
                },
            }
        time.sleep(poll_seconds)

    return {
        "ok": False,
        "status": "resolution_failed",
        "action": action,
        "blocker": {"type": blocker["type"]},
        "error": "click_not_confirmed",
    }





def _win32_owner(hwnd):
    """Owner window handle for ``hwnd``, or 0 when it has none."""
    user32, wintypes, ctypes = _load_win32_modules()
    get_window = user32.GetWindow
    get_window.restype = wintypes.HWND
    get_window.argtypes = [wintypes.HWND, wintypes.UINT]
    return get_window(hwnd, GW_OWNER)


def _win32_is_enabled(hwnd):
    user32, wintypes, ctypes = _load_win32_modules()
    is_window_enabled = user32.IsWindowEnabled
    is_window_enabled.restype = wintypes.BOOL
    is_window_enabled.argtypes = [wintypes.HWND]
    return bool(is_window_enabled(hwnd))


def _win32_owner_enabled(hwnd):
    """True when the owner window exists and is enabled (not blocked by a modal)."""
    owner = _win32_owner(hwnd)
    if not owner:
        return True
    return _win32_is_enabled(owner)


def _win32_style(hwnd):
    user32, wintypes, ctypes = _load_win32_modules()
    get_window_long = user32.GetWindowLongW
    get_window_long.restype = wintypes.LONG
    get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
    return get_window_long(hwnd, GWL_STYLE)


def _win32_window_rect(hwnd):
    """Window rect as ``(left, top, right, bottom)``, or None when unreadable."""
    user32, wintypes, ctypes = _load_win32_modules()
    get_window_rect = user32.GetWindowRect
    get_window_rect.restype = wintypes.BOOL
    get_window_rect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    rect = wintypes.RECT()
    if not get_window_rect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def _is_dialog_style(hwnd):
    style = _win32_style(hwnd)
    return bool(style & WS_POPUP)


def _is_modal_sized(hwnd):
    rect = _win32_window_rect(hwnd)
    if rect is None:
        return False
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return False
    return width <= MAX_MODAL_DIALOG_EDGE_PX and height <= MAX_MODAL_DIALOG_EDGE_PX


def _is_modal_window(hwnd):
    """True when ``hwnd`` blocks its owner rather than merely being visible.

    The window must first look like a dialog (popup style, prompt-sized). Only
    then is owner state consulted: a true modal disables the window that owns
    it. Requiring both halves matters, because a disabled owner alone also
    matches non-blocking Editor panels (Preferences, Project Settings) whenever
    some unrelated window has disabled their owner.

    Dialogs that appear before Unity's main window (Safe Mode) have no owner, so
    dialog styling plus size is sufficient on its own for those.

    Anything failing these tests is treated as non-blocking: a false positive
    costs the caller a hang, while a false negative costs one extra re-check.
    """
    if not _is_dialog_style(hwnd) or not _is_modal_sized(hwnd):
        return False
    owner = _win32_owner(hwnd)
    if owner and not _win32_owner_enabled(hwnd):
        return True
    # Ownerless dialog: style and size are the whole signal. An owned dialog
    # whose owner is still enabled is not blocking the Editor.
    return owner == 0


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

def _match_dialog_spec(dialog):
    """Map a window to its catalog spec.

    Title-keyed specs are checked first. The ScriptUpdater consent dialog is
    matched by its message body because its title is not stable across Editor
    versions.
    """
    spec = WINDOWS_DIALOG_SPECS.get(dialog["title"])
    if spec is not None:
        return spec
    body = dialog.get("body") or ""
    if body:
        for body_spec in WINDOWS_BODY_DIALOG_SPECS:
            fingerprints = body_spec.get("message_fingerprints")
            if fingerprints:
                if any(fp in body for fp in fingerprints):
                    return body_spec
            elif body_spec.get("message_fingerprint") and body_spec["message_fingerprint"] in body:
                return body_spec
    return None


def _dialog_entry(dialog, spec):
    entry = {
        "hwnd": dialog["hwnd"],
        "title": dialog["title"],
        "type": spec["type"],
        "cancel_labels": spec["cancel_labels"],
        "click_method": spec.get("click_method", "bm_click"),
    }
    return entry


def _list_supported_windows_dialogs(unity_pid):
    """Dialogs a caller may resolve: catalog types plus reported unknowns."""
    dialogs = []
    for dialog in _list_windows_dialogs(unity_pid):
        spec = _match_dialog_spec(dialog)
        if spec is not None and spec["type"] == API_UPDATER_DIALOG_TYPE:
            # The ScriptUpdater consent dialog is auto-recovered, never resolved
            # through resolve-blocker.
            continue
        if spec is None:
            if not _is_modal_window(dialog["hwnd"]):
                continue
            dialogs.append(_unknown_dialog_entry(dialog))
            continue
        dialogs.append(_dialog_entry(dialog, spec))
    return dialogs


def _unknown_dialog_entry(dialog):
    entry = {
        "hwnd": dialog["hwnd"],
        "title": dialog["title"],
        "type": UNKNOWN_DIALOG_TYPE,
        "cancel_labels": (),
        "click_method": "bm_click",
    }
    return entry


def _list_supported_api_updater_dialogs(unity_pid):
    """Visible ScriptUpdater consent dialogs for a Unity process."""
    dialogs = []
    for dialog in _list_windows_dialogs(unity_pid):
        spec = _match_dialog_spec(dialog)
        if spec is None or spec["type"] != API_UPDATER_DIALOG_TYPE:
            continue
        dialogs.append(_dialog_entry(dialog, spec))
    return dialogs


def dismiss_api_updater_dialog(
    unity_pid,
    timeout_ms=DEFAULT_API_UPDATER_DISMISS_TIMEOUT_MS,
    poll_interval_ms=DEFAULT_API_UPDATER_DISMISS_POLL_MS,
    list_dialogs_fn=None,
    click_fn=None,
    time_ref=None,
):
    """Auto-decline every visible ScriptUpdater consent dialog for a Unity process.

    Clicks No (never Yes, never Enter) and repeats while the dialog reappears
    inside a bounded window, because Unity can prompt once per compilation unit.
    Returns a dict with ``dismissed`` counting distinct dialogs declined.
    """
    time_ref = time if time_ref is None else time_ref
    if not unity_pid or sys.platform != "win32":
        return {"ok": False, "status": "unsupported", "dismissed": 0}
    list_dialogs_fn = _list_supported_api_updater_dialogs if list_dialogs_fn is None else list_dialogs_fn
    click_fn = _click_cancel_button if click_fn is None else click_fn

    deadline = time_ref.time() + (max(timeout_ms, 1) / 1000.0)
    poll_seconds = max(poll_interval_ms, 1) / 1000.0
    dismissed_hwnds = set()
    dismissed = 0

    while True:
        dialogs = list_dialogs_fn(unity_pid)
        fresh = [dialog for dialog in dialogs if dialog["hwnd"] not in dismissed_hwnds]
        if fresh:
            if time_ref.time() >= deadline:
                return {
                    "ok": dismissed > 0,
                    "status": "dismissed" if dismissed else "timeout",
                    "dismissed": dismissed,
                }
            dialog = fresh[0]
            if not click_fn(dialog):
                return {"ok": False, "status": "click_failed", "dismissed": dismissed}
            dismissed_hwnds.add(dialog["hwnd"])
            dismissed += 1
            time_ref.sleep(poll_seconds)
            continue
        # Nothing new to click. Confirm previously dismissed windows are gone
        # before reporting success; a dialog that refuses to close keeps polling
        # until the bounded window expires.
        if dismissed == 0:
            return {"ok": False, "status": "no_dialog", "dismissed": 0}
        still_present = [dialog for dialog in dialogs if dialog["hwnd"] in dismissed_hwnds]
        if not still_present:
            return {"ok": True, "status": "dismissed", "dismissed": dismissed}
        if time_ref.time() >= deadline:
            return {
                "ok": dismissed > 0,
                "status": "dismissed" if dismissed else "timeout",
                "dismissed": dismissed,
            }
        time_ref.sleep(poll_seconds)


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
            dialogs.append({"hwnd": hwnd, "title": title, "body": _read_dialog_body_text(hwnd)})
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


def _enumerate_child_controls(dialog_hwnd):
    """Every child control of a dialog as ``{hwnd, class_name, label, ctrl_id}``."""
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

    found = []

    def callback(hwnd, _l_param):
        class_name = _get_window_text(hwnd, None, get_class_name, ctypes, buffer_size=256)
        label = _get_window_text(hwnd, get_window_text_length, get_window_text, ctypes)
        found.append(
            {
                "hwnd": hwnd,
                "class_name": class_name,
                "label": label,
                "ctrl_id": get_dlg_ctrl_id(hwnd),
            }
        )
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    enum_child_windows(dialog_hwnd, enum_proc, 0)
    return found


def _is_control_clickable(hwnd):
    control_style = _win32_style(hwnd)
    if control_style & WS_DISABLED:
        return False
    if not _win32_is_visible(hwnd):
        return False
    return (control_style & 0x000F) not in NON_CLICKABLE_BUTTON_STYLES


def _enumerate_buttons(dialog_hwnd):
    """Clickable push buttons of a dialog as ``{hwnd, label, ctrl_id}``.

    Win32 reports checkboxes, radio buttons, and group boxes under the same
    "Button" class as push buttons, and ``EnumChildWindows`` recurses into
    nested containers, so filtering by class alone would surface controls a
    caller should never click. Disabled and invisible controls are excluded for
    the same reason: a control that cannot be clicked is not a candidate.
    """
    buttons = []
    for control in _enumerate_child_controls(dialog_hwnd):
        if control["class_name"] != "Button":
            continue
        if not _is_control_clickable(control["hwnd"]):
            continue
        buttons.append(
            {
                "hwnd": control["hwnd"],
                "label": control["label"],
                "ctrl_id": control["ctrl_id"],
            }
        )
    return buttons


def _normalize_button_label(label):
    """Strip ``&`` mnemonics and surrounding whitespace for matching."""
    return (label or "").replace("&", "").strip()


def _match_button(buttons, wanted):
    """Find a button whose label matches ``wanted``, or None."""
    target = _normalize_button_label(wanted)
    if not target:
        return None
    lowered = target.lower()
    for button in buttons:
        label = _normalize_button_label(button["label"])
        if label == target or label.lower() == lowered:
            return button
    return None


def _win32_is_visible(hwnd):
    user32, wintypes, ctypes = _load_win32_modules()
    is_window_visible = user32.IsWindowVisible
    is_window_visible.restype = wintypes.BOOL
    is_window_visible.argtypes = [wintypes.HWND]
    return bool(is_window_visible(hwnd))


def _send_button_message(button_hwnd):
    """Level 1 of the click chain: ``BM_CLICK``, which steals no focus."""
    user32, wintypes, ctypes = _load_win32_modules()
    send_message = user32.SendMessageW
    send_message.restype = wintypes.LPARAM
    send_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    send_message(button_hwnd, BM_CLICK, 0, 0)
    return True


def _send_command_message(dialog_hwnd, button):
    """Level 2 of the click chain: ``WM_COMMAND`` with the button's control id."""
    user32, wintypes, ctypes = _load_win32_modules()
    send_message = user32.SendMessageW
    send_message.restype = wintypes.LPARAM
    send_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    wparam = wintypes.WPARAM((BN_CLICKED << 16) | (button.get("ctrl_id") or 0))
    send_message(dialog_hwnd, WM_COMMAND, wparam, wintypes.LPARAM(button["hwnd"]))
    return True


def _post_key_return(button_hwnd):
    """Level 3 of the click chain: posted key messages, still no foregrounding."""
    user32, wintypes, ctypes = _load_win32_modules()
    post_message = user32.PostMessageW
    post_message.restype = wintypes.BOOL
    post_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    post_message(button_hwnd, WM_KEYDOWN, wintypes.WPARAM(VK_RETURN), 0)
    post_message(button_hwnd, WM_KEYUP, wintypes.WPARAM(VK_RETURN), 0)
    return True


def _click_button(dialog_hwnd, button):
    """Activate a button preferring message-level methods over foregrounding.

    Safe Mode is exempt and keeps the foreground keyboard path; callers dispatch
    to ``_click_via_keyboard`` for it instead of using this chain.
    """
    _send_button_message(button["hwnd"])
    if not _is_window_present(dialog_hwnd):
        return True
    _send_command_message(dialog_hwnd, button)
    if not _is_window_present(dialog_hwnd):
        return True
    _post_key_return(button["hwnd"])
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


def _read_dialog_body_text(dialog_hwnd):
    """Concatenated Static child text of a dialog, used to fingerprint its message.

    The ScriptUpdater consent dialog's title is not a stable identifier, so the
    message sentence is read from the dialog body. Returns "" when nothing can be
    read (non-Windows, no children, or a dialog whose tree is not standard).
    """
    if sys.platform != "win32":
        return ""
    user32, wintypes, ctypes = _load_win32_modules()
    enum_child_windows = user32.EnumChildWindows
    get_class_name = user32.GetClassNameW
    get_window_text_length = user32.GetWindowTextLengthW
    get_window_text = user32.GetWindowTextW

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

    parts = []

    def callback(hwnd, _l_param):
        class_name = _get_window_text(hwnd, None, get_class_name, ctypes, buffer_size=256)
        if class_name != "Static":
            return True
        text = _get_window_text(hwnd, get_window_text_length, get_window_text, ctypes)
        if text:
            parts.append(text)
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    enum_child_windows(dialog_hwnd, enum_proc, 0)
    return "\n".join(parts)


def _load_win32_modules():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    return user32, wintypes, ctypes
