"""Fake user32 double so Windows dialog logic can be tested without a real Win32 API.

Every win32 call in :mod:`unity_modal_blockers` goes through ``_load_win32_modules()``,
which returns ``(user32, wintypes, ctypes)``. Tests patch that single function to
return a :class:`FakeUser32` in place of ``user32`` while keeping the real ``wintypes``
and ``ctypes``, so ctypes buffer and callback machinery stays genuine and only the
user32 surface is scripted.

The double is intentionally shallow: it implements only the calls the modal-blocker
code makes, and it records every call so tests can assert on interaction order (for
example that a click never called ``SetForegroundWindow``).
"""

import ctypes
from ctypes import wintypes


GW_OWNER = 4
GWL_STYLE = -16

WS_DISABLED = 0x08000000
WS_VISIBLE = 0x10000000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_CAPTION = 0x00C00000
DS_MODALFRAME = 0x0080

# Editor main windows and dockable panels are overlapped windows, not popups.
# Fixtures must not give them dialog style, or the style fallback would classify
# them as ownerless modals.
WS_OVERLAPPEDWINDOW = 0x00CF0000
MAIN_WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
MAIN_WINDOW_RECT = (0, 0, 1600, 1000)
# Unity's own windows are UnityContainerWndClass, never #32770.
UNITY_WINDOW_CLASS = "UnityContainerWndClass"
DIALOG_CLASS = "#32770"
PANEL_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
PANEL_RECT = (100, 100, 1100, 800)

BS_CHECKBOX = 0x0002
BS_AUTOCHECKBOX = 0x0003
BS_RADIOBUTTON = 0x0004
BS_3STATE = 0x0005
BS_AUTO3STATE = 0x0006
BS_GROUPBOX = 0x0007
BS_AUTORADIOBUTTON = 0x0009

BM_CLICK = 0x00F5
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
BN_CLICKED = 0
VK_RETURN = 0x0D


def _style(low_word):
    """Build a window style with the given low word (button styles live there)."""
    return WS_CHILD | WS_VISIBLE | low_word


def main_window(hwnd, title="Unity Editor", **kwargs):
    """A realistic Editor main window: overlapped, large, not dialog-styled."""
    kwargs.setdefault("style", MAIN_WINDOW_STYLE)
    kwargs.setdefault("rect", MAIN_WINDOW_RECT)
    kwargs.setdefault("class_name", UNITY_WINDOW_CLASS)
    return FakeWindow(hwnd, title=title, **kwargs)


def panel(hwnd, title, owner_hwnd):
    """A non-blocking Editor panel such as Preferences or Project Settings."""
    return FakeWindow(
        hwnd,
        title=title,
        class_name=UNITY_WINDOW_CLASS,
        style=PANEL_STYLE,
        rect=PANEL_RECT,
        owner=owner_hwnd,
    )


def unity_window(hwnd, title, owner_hwnd=None, rect=(100, 100, 700, 900)):
    """A Unity Editor window (UnityContainerWndClass): popup-styled but not a dialog.

    Observed on the validation host: these windows see a disabled owner while a
    real modal is up, so style and size alone would report them as blockers.
    """
    return FakeWindow(
        hwnd,
        title=title,
        class_name=UNITY_WINDOW_CLASS,
        style=WS_POPUP | WS_VISIBLE,
        rect=rect,
        owner=owner_hwnd,
    )


def file_dialog(hwnd, title, owner_hwnd, rect=(100, 100, 1300, 820)):
    """A Windows common dialog, class #32770, as the real Save Scene dialog is.

    Measured at 1200x720 on the validation host -- larger than a prompt, so a
    prompt-size bound must not reject it.
    """
    return FakeWindow(hwnd, title=title, class_name=DIALOG_CLASS, style=WS_POPUP | WS_VISIBLE, rect=rect, owner=owner_hwnd)


def button(hwnd, label, ctrl_id=None, **kwargs):
    """A clickable push button child control."""
    window = FakeWindow(hwnd, title=label, class_name="Button", style=_style(0), **kwargs)
    if ctrl_id is not None:
        window.hwnd = ctrl_id
    return window


def static_text(hwnd, text):
    """A Static child control, used for dialog body text."""
    return FakeWindow(hwnd, title=text, class_name="Static", style=_style(0))


class FakeWindow:
    """A scripted window or child control.

    Defaults model a top-level dialog. Use :func:`main_window` and
    :func:`panel` for the non-dialog windows the discriminator must reject.
    """

    def __init__(
        self,
        hwnd,
        title="",
        class_name=DIALOG_CLASS,
        style=WS_POPUP | WS_CAPTION,
        visible=True,
        enabled=True,
        owner=None,
        rect=(0, 0, 400, 300),
        children=(),
        pid=None,
    ):
        self.hwnd = hwnd
        self.title = title
        self.class_name = class_name
        self.style = style
        self.visible = visible
        self.enabled = enabled
        self.owner = owner
        self.rect = rect
        self.children = list(children)
        self.pid = pid
        # Tests flip this to simulate a dialog that closes in response to a click.
        self.auto_close = False

    def with_children(self, *children):
        self.children.extend(children)
        return self

    def __repr__(self):
        return "FakeWindow(hwnd={!r}, title={!r}, class_name={!r})".format(
            self.hwnd, self.title, self.class_name
        )


def _deref(ref):
    """Unwrap a ``ctypes.byref()`` argument to the underlying ctypes object.

    Production code passes struct out-parameters with ``ctypes.byref(rect)``,
    which arrives here as a ``CArgObject`` rather than the RECT/DWORD itself.
    """
    inner = getattr(ref, "_obj", None)
    return inner if inner is not None else ref


class _FakeFunc:
    """Callable stand-in for a ctypes function pointer.

    Production code assigns ``.restype`` and ``.argtypes`` to each looked-up
    function. A bound method cannot take those attributes, so the double exposes
    callable objects instead.
    """

    def __init__(self, name, fn, calls):
        self._name = name
        self._fn = fn
        self._calls = calls
        self.restype = None
        self.argtypes = None

    def __call__(self, *args):
        self._calls.append((self._name, args))
        return self._fn(*args)


class FakeUser32:
    """Scripted user32 surface backed by a tree of :class:`FakeWindow`."""

    def __init__(self, windows, pid=4321):
        self.windows = list(windows)
        self.pid = pid
        self.calls = []
        self.foregrounded = None

    # --- lookup helpers -------------------------------------------------

    def _all(self):
        out = []
        pending = list(self.windows)
        while pending:
            window = pending.pop(0)
            out.append(window)
            pending.extend(window.children)
        return out

    def _find(self, hwnd):
        for window in self._all():
            if window.hwnd == hwnd:
                return window
        return None

    # --- enumeration ----------------------------------------------------

    def _enum(self, windows, enum_proc, lparam):
        for window in windows:
            if not enum_proc(window.hwnd, lparam):
                return False
        return True

    def EnumWindows(self, enum_proc, lparam):
        # The real EnumWindows walks top-level windows only; children are
        # reachable solely through EnumChildWindows. Recursing here would make
        # every dialog button look like a window of its own.
        return self._enum(self.windows, enum_proc, lparam)

    def EnumChildWindows(self, parent, enum_proc, lparam):
        window = self._find(parent)
        if window is None:
            return False
        return self._enum(window.children, enum_proc, lparam)

    # --- window properties ----------------------------------------------

    def IsWindow(self, hwnd):
        return self._find(hwnd) is not None

    def IsWindowVisible(self, hwnd):
        window = self._find(hwnd)
        return bool(window and window.visible)

    def IsWindowEnabled(self, hwnd):
        window = self._find(hwnd)
        return bool(window and window.enabled)

    def GetWindow(self, hwnd, cmd):
        window = self._find(hwnd)
        if window is None:
            return 0
        if cmd == GW_OWNER:
            return window.owner if window.owner else 0
        return 0

    def GetWindowLongW(self, hwnd, index):
        window = self._find(hwnd)
        if window is None or index != GWL_STYLE:
            return 0
        return window.style

    def GetWindowThreadProcessId(self, hwnd, ref):
        _deref(ref).value = self.pid
        return self.pid

    def GetWindowRect(self, hwnd, ref):
        window = self._find(hwnd)
        if window is None:
            return False
        left, top, right, bottom = window.rect
        rect = _deref(ref)
        rect.left, rect.top, rect.right, rect.bottom = left, top, right, bottom
        return True

    def GetDlgCtrlID(self, hwnd):
        window = self._find(hwnd)
        return window.hwnd if window is not None else 0

    # --- text -----------------------------------------------------------

    def GetWindowTextLengthW(self, hwnd):
        window = self._find(hwnd)
        return len(window.title) if window is not None else 0

    def GetWindowTextW(self, hwnd, buffer, count):
        window = self._find(hwnd)
        if window is None:
            buffer.value = ""
            return 0
        text = window.title[: count - 1] if count > 1 else ""
        buffer.value = text
        return len(text)

    def GetClassNameW(self, hwnd, buffer, count):
        window = self._find(hwnd)
        if window is None:
            buffer.value = ""
            return 0
        name = window.class_name[: count - 1] if count > 1 else ""
        buffer.value = name
        return len(name)

    # --- activation -----------------------------------------------------

    def SendMessageW(self, hwnd, msg, wparam, lparam):
        self._maybe_close(hwnd, msg)
        return 1

    def PostMessageW(self, hwnd, msg, wparam, lparam):
        self._maybe_close(hwnd, msg)
        return True

    def SetForegroundWindow(self, hwnd):
        self.foregrounded = hwnd
        return True

    def keybd_event(self, vk, scan, flags, extra):
        # The keyboard path targets the dialog itself, which the caller has just
        # foregrounded; a scripted dialog closes on the Enter key.
        target = self._find(getattr(self, "foregrounded", None))
        if target is not None and target.auto_close:
            target.visible = False
        return None

    def mouse_event(self, flags, dx, dy, data, extra):
        return None

    def SetCursorPos(self, x, y):
        return True

    def _maybe_close(self, hwnd, msg):
        """Simulate a dialog closing when a message reaches an auto_close control."""
        if msg not in (BM_CLICK, WM_COMMAND, WM_KEYDOWN):
            return
        dialog = self._toplevel_of(hwnd)
        # auto_close may be set on the dialog or on the clicked control.
        clicked = self._find(hwnd)
        if dialog is None or not (dialog.auto_close or (clicked and clicked.auto_close)):
            return
        dialog.visible = False

    def _toplevel_of(self, hwnd):
        """Top-level window containing ``hwnd``."""
        for window in self.windows:
            if window.hwnd == hwnd:
                return window
            if any(child.hwnd == hwnd for child in self._all_of(window)):
                return window
        return None

    def _all_of(self, window):
        out = []
        pending = list(window.children)
        while pending:
            child = pending.pop(0)
            out.append(child)
            pending.extend(child.children)
        return out

    # --- ctypes surface -------------------------------------------------

    def bind(self):
        """Return this double as a user32 replacement with recordable callables."""
        names = [
            "EnumWindows",
            "EnumChildWindows",
            "IsWindow",
            "IsWindowVisible",
            "IsWindowEnabled",
            "GetWindow",
            "GetWindowLongW",
            "GetWindowThreadProcessId",
            "GetWindowRect",
            "GetDlgCtrlID",
            "GetWindowTextLengthW",
            "GetWindowTextW",
            "GetClassNameW",
            "SendMessageW",
            "PostMessageW",
            "SetForegroundWindow",
            "keybd_event",
            "mouse_event",
            "SetCursorPos",
        ]
        for name in names:
            setattr(self, name, _FakeFunc(name, getattr(self, name), self.calls))
        return self

    def names_called(self):
        return [name for name, _args in self.calls]

    def called(self, name):
        return any(called == name for called, _args in self.calls)


def install(module, windows, pid=4321):
    """Patch ``module._load_win32_modules`` to return a scripted user32.

    Returns a context manager yielding the :class:`FakeUser32`, so a test can
    assert on recorded calls after exercising the module.
    """
    user32 = FakeUser32(windows, pid=pid).bind()

    def _load():
        return user32, wintypes, ctypes

    original = module._load_win32_modules

    class _Patch:
        def __enter__(self):
            module._load_win32_modules = _load
            return user32

        def __exit__(self, *exc_info):
            module._load_win32_modules = original
            return False

    return _Patch()
