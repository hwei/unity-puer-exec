import ctypes
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests import fake_user32  # type: ignore
import unity_modal_blockers  # type: ignore


def _dialog(hwnd, title="Dialog", **kwargs):
    return fake_user32.FakeWindow(hwnd, title=title, **kwargs)


def _button(hwnd, label, ctrl_id=None, **kwargs):
    return fake_user32.FakeWindow(
        hwnd,
        title=label,
        class_name="Button",
        style=fake_user32._style(0),
        **kwargs,
    )


class HarnessSmokeTests(unittest.TestCase):
    """The harness must faithfully expose the calls the blocker code makes."""

    def test_tree_is_readable_through_real_ctypes_buffers(self):
        owner = _dialog(1, title="Main")
        child = _button(2, "&Save")
        owner.with_children(child)

        with fake_user32.install(unity_modal_blockers, [owner]) as user32:
            read = unity_modal_blockers._read_dialog_body_text(1)
            title = unity_modal_blockers._list_windows_dialogs(4321)

        # Any descendant's readable text counts, whatever its window class: a
        # class filter is what hid the ScriptUpdater message.
        self.assertEqual(read, "&Save")
        self.assertEqual(len(title), 1)
        self.assertEqual(title[0]["title"], "Main")
        self.assertEqual(title[0]["body"], "&Save")
        self.assertEqual(title[0]["body_outcome"], unity_modal_blockers.DIALOG_BODY_READ)

    def test_childless_dialog_names_the_absent_text_condition(self):
        owner = _dialog(1, title="Main")

        with fake_user32.install(unity_modal_blockers, [owner]):
            body = unity_modal_blockers._read_dialog_body(1)

        self.assertEqual(body["text"], "")
        self.assertEqual(
            body["outcome"], unity_modal_blockers.DIALOG_BODY_NO_READABLE_TEXT
        )

    def test_stale_handle_names_the_enumeration_failure(self):
        owner = _dialog(1, title="Main")

        with fake_user32.install(unity_modal_blockers, [owner]):
            body = unity_modal_blockers._read_dialog_body(999)

        self.assertEqual(body["text"], "")
        self.assertEqual(
            body["outcome"], unity_modal_blockers.DIALOG_BODY_ENUMERATION_FAILED
        )

    def test_owner_lookup(self):
        owner = _dialog(1, title="Main")
        modal = _dialog(2, title="Save Scene", owner=1)
        owner.enabled = False

        with fake_user32.install(unity_modal_blockers, [owner, modal]):
            self.assertEqual(unity_modal_blockers._win32_owner(2), 1)
            self.assertFalse(unity_modal_blockers._win32_owner_enabled(2))
            self.assertEqual(unity_modal_blockers._win32_owner(1), 0)

    def test_style_and_rect_reads(self):
        window = _dialog(7, rect=(10, 20, 410, 320))

        with fake_user32.install(unity_modal_blockers, [window]) as user32:
            style = user32.GetWindowLongW(7, fake_user32.GWL_STYLE)
            rect = unity_modal_blockers._win32_window_rect(7)

        self.assertEqual(style, window.style)
        self.assertEqual(rect, (10, 20, 410, 320))

    def test_child_enumeration_reads_class_and_id(self):
        dialog = _dialog(1)
        dialog.with_children(_button(2, "&Save"), _button(3, "Cancel"))

        with fake_user32.install(unity_modal_blockers, [dialog]):
            controls = unity_modal_blockers._enumerate_child_controls(1)

        self.assertEqual([c["label"] for c in controls], ["&Save", "Cancel"])
        self.assertEqual([c["class_name"] for c in controls], ["Button", "Button"])

    def test_messages_are_recorded(self):
        dialog = _dialog(1)
        button = _button(2, "&Save")
        dialog.with_children(button)

        with fake_user32.install(unity_modal_blockers, [dialog]) as user32:
            unity_modal_blockers._send_button_message(2)
            unity_modal_blockers._post_key_return(2)

        self.assertIn("SendMessageW", user32.names_called())
        self.assertIn("PostMessageW", user32.names_called())

    def test_click_closes_an_auto_close_dialog(self):
        dialog = _dialog(1)
        button = _button(2, "&Save", owner=1)
        button.auto_close = True
        dialog.with_children(button)

        with fake_user32.install(unity_modal_blockers, [dialog]):
            self.assertTrue(unity_modal_blockers._is_window_present(1))
            unity_modal_blockers._send_button_message(2)
            self.assertFalse(unity_modal_blockers._is_window_present(1))


class CrossProcessTextReadTests(unittest.TestCase):
    """The double must reproduce the measured foreign-control text divergence.

    Win32 answers ``GetWindowTextW`` for a foreign child control with a cached
    stub, while ``WM_GETTEXT`` returns the control's real text. An in-process
    fake that answers both the same way cannot tell "the product read the
    message" from "the product read a stub", which is exactly how the
    ScriptUpdater consent dialog shipped unreadable with a green mocked suite.
    """

    REAL_TEXT = "Some of this projects source files refer to API that has changed."
    STUB = "Static"

    def _read_through_buffer(self, user32, hwnd):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, len(buf))
        return buf.value

    def test_foreign_control_answers_get_window_text_with_the_stub(self):
        dialog = _dialog(1, title="Script Updating Consent")
        dialog.with_children(fake_user32.foreign_control(2, self.REAL_TEXT))

        with fake_user32.install(unity_modal_blockers, [dialog]) as user32:
            text = self._read_through_buffer(user32, 2)
            length = user32.GetWindowTextLengthW(2)

        self.assertEqual(
            text,
            self.STUB,
            "GetWindowTextW must answer the cached stub for a foreign control; "
            "answering the real text removes the cross-process read the product "
            "depends on",
        )
        self.assertEqual(
            length,
            len(self.STUB),
            "GetWindowTextLengthW must report the stub length for a foreign control; "
            "reporting the real text collapses the cross-process divergence",
        )

    def test_foreign_control_answers_wm_gettext_with_the_real_text(self):
        dialog = _dialog(1, title="Script Updating Consent")
        dialog.with_children(fake_user32.foreign_control(2, self.REAL_TEXT))

        with fake_user32.install(unity_modal_blockers, [dialog]):
            body = unity_modal_blockers._read_dialog_body(1)

        self.assertEqual(
            body["outcome"],
            unity_modal_blockers.DIALOG_BODY_READ,
            "WM_GETTEXT must answer a foreign control with its real text; "
            "the cross-process read is what makes the body readable",
        )
        self.assertEqual(
            body["text"],
            self.REAL_TEXT,
            "the body must be the WM_GETTEXT answer, not the GetWindowTextW stub",
        )

    def test_body_reader_returns_the_message_not_the_stub(self):
        # The end the double exists to protect: the product's own reader must
        # take the WM_GETTEXT path, not the cached GetWindowTextW stub.
        dialog = _dialog(1, title="Script Updating Consent")
        dialog.with_children(
            fake_user32.static_text(3, ""),
            fake_user32.foreign_control(2, self.REAL_TEXT),
            _button(4, "&No"),
        )

        with fake_user32.install(unity_modal_blockers, [dialog]):
            body = unity_modal_blockers._read_dialog_body(1)

        self.assertEqual(
            body["outcome"],
            unity_modal_blockers.DIALOG_BODY_READ,
            "the reader must read the foreign control's message across the "
            "process boundary, not report an empty body",
        )
        self.assertIn(
            self.REAL_TEXT,
            body["text"],
            "the product must read the WM_GETTEXT answer (the cross-process read), "
            "not the cached GetWindowTextW stub",
        )
        self.assertNotIn(
            self.STUB,
            body["text"].split("\n"),
            "the cached GetWindowTextW stub must not reach the dialog body",
        )

    def test_control_that_ignores_wm_gettext_falls_back_to_get_window_text(self):
        # A same-process control that does not answer the message is the case
        # the GetWindowTextW fallback exists for: its text is readable there.
        dialog = _dialog(1, title="Script Updating Consent")
        dialog.with_children(
            fake_user32.FakeWindow(
                2,
                title="readable fallback text",
                class_name="SysLink",
                style=fake_user32._style(0),
                answer_wm_gettext=False,
            )
        )

        with fake_user32.install(unity_modal_blockers, [dialog]) as user32:
            body = unity_modal_blockers._read_dialog_body(1)

        self.assertEqual(
            body["outcome"],
            unity_modal_blockers.DIALOG_BODY_READ,
            "an unanswered WM_GETTEXT must reach the GetWindowTextW fallback, "
            "not produce an empty body",
        )
        self.assertEqual(body["text"], "readable fallback text")
        # The double must report the message as unanswered, and the product must
        # then have taken the same-process read.
        self.assertIn("SendMessageTimeoutW", user32.names_called())
        self.assertIn(
            "GetWindowTextW",
            user32.names_called(),
            "the fallback path must be exercised, not silently skipped",
        )


if __name__ == "__main__":
    unittest.main()
