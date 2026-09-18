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

        self.assertEqual(read, "")
        self.assertEqual(len(title), 1)
        self.assertEqual(title[0]["title"], "Main")

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


if __name__ == "__main__":
    unittest.main()
