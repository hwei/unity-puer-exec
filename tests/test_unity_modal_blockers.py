import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from tests import fake_user32  # type: ignore
import unity_modal_blockers  # type: ignore


class _FakeClock:
    def __init__(self):
        self.current = 0.0

    def time(self):
        return self.current

    def sleep(self, seconds):
        self.current += seconds


class ApiUpdaterDialogMatchingTests(unittest.TestCase):
    def test_matches_by_message_body_not_title(self):
        dialog = {
            "hwnd": 11,
            "title": "Unity",
            "body": (
                "Some of this project's source files refer to API that has changed.\n"
                "Would you like Unity to update them?"
            ),
        }

        spec = unity_modal_blockers._match_dialog_spec(dialog)

        self.assertIsNotNone(spec)
        self.assertEqual(spec["type"], unity_modal_blockers.API_UPDATER_DIALOG_TYPE)
        self.assertEqual(spec["click_method"], "bm_click")
        self.assertIn("No", spec["cancel_labels"])

    def test_matches_typo_and_invariant_message_bodies(self):
        bodies = [
            (
                "Some of this projects source files refer to API that has changed. "
                "These can be automatically updated. It is recommended to have a backup "
                "of the project before updating. Do you want these files to be updated?"
            ),
            "Warning: source files refer to API that has changed. Update now?",
        ]
        for idx, body in enumerate(bodies):
            dialog = {"hwnd": 100 + idx, "title": "API Updating", "body": body}
            spec = unity_modal_blockers._match_dialog_spec(dialog)
            self.assertIsNotNone(spec, f"Failed to match body: {body}")
            self.assertEqual(spec["type"], unity_modal_blockers.API_UPDATER_DIALOG_TYPE)

    def test_is_api_updater_message(self):
        self.assertTrue(
            unity_modal_blockers.is_api_updater_message(
                "Some of this project's source files refer to API that has changed"
            )
        )
        self.assertTrue(
            unity_modal_blockers.is_api_updater_message(
                "Some of this projects source files refer to API that has changed"
            )
        )
        self.assertTrue(
            unity_modal_blockers.is_api_updater_message(
                "Some arbitrary prefix source files refer to API that has changed suffix"
            )
        )
        self.assertFalse(unity_modal_blockers.is_api_updater_message("Some unrelated dialog body"))
        self.assertFalse(unity_modal_blockers.is_api_updater_message(""))
        self.assertFalse(unity_modal_blockers.is_api_updater_message(None))

    def test_body_without_the_fingerprint_does_not_match(self):
        dialog = {"hwnd": 12, "title": "Unity", "body": "Some unrelated dialog body"}

        self.assertIsNone(unity_modal_blockers._match_dialog_spec(dialog))

    def test_title_keyed_catalog_dialogs_still_match(self):
        dialog = {"hwnd": 13, "title": "Enter Safe Mode?", "body": ""}

        spec = unity_modal_blockers._match_dialog_spec(dialog)

        self.assertIsNotNone(spec)
        self.assertEqual(spec["type"], "safe_mode_dialog")

    def test_supported_blocker_listing_excludes_the_consent_dialog(self):
        consent = {
            "hwnd": 14,
            "title": "Unity",
            "body": unity_modal_blockers.API_UPDATER_MESSAGE_FINGERPRINT,
        }
        save_scene = {"hwnd": 15, "title": "Save Scene", "body": ""}
        with mock.patch.object(
            unity_modal_blockers, "_list_windows_dialogs", return_value=[consent, save_scene]
        ), mock.patch.object(unity_modal_blockers.sys, "platform", "win32"):
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual([b["type"] for b in blockers], ["save_scene_dialog"])

    def test_supported_dialog_listing_copies_click_method_for_safe_mode(self):
        safe_mode = {"hwnd": 16, "title": "Enter Safe Mode?", "body": ""}
        with mock.patch.object(
            unity_modal_blockers, "_list_windows_dialogs", return_value=[safe_mode]
        ):
            dialogs = unity_modal_blockers._list_supported_windows_dialogs(4321)

        self.assertEqual(len(dialogs), 1)
        self.assertEqual(dialogs[0]["click_method"], "keyboard")
        self.assertEqual(dialogs[0]["cancel_labels"], ("&Enter Safe Mode", "Enter Safe Mode"))


def _main(hwnd, title="Unity Editor", **kwargs):
    """A realistic Editor main window: overlapped, large, not dialog-styled."""
    return fake_user32.main_window(hwnd, title=title, **kwargs)


def _panel(hwnd, title, owner_hwnd):
    """A non-blocking Editor panel such as Preferences or Project Settings."""
    return fake_user32.panel(hwnd, title, owner_hwnd)


def _button(hwnd, label, **kwargs):
    return fake_user32.button(hwnd, label, **kwargs)


def _dialog(hwnd, title, **kwargs):
    """A top-level dialog: popup-styled and prompt-sized, as dialogs really are."""
    kwargs.setdefault("rect", (200, 200, 640, 380))
    return fake_user32.FakeWindow(hwnd, title=title, **kwargs)


class ModalDiscriminationTests(unittest.TestCase):
    """D2: a visible titled window is not evidence of blocking on its own."""

    def test_owner_disabled_window_is_a_modal(self):
        owner = _main(1, enabled=False)
        modal = _dialog(2, "Save Scene", owner=1)

        with fake_user32.install(unity_modal_blockers, [owner, modal]):
            self.assertTrue(unity_modal_blockers._is_modal_window(2))

    def test_owner_enabled_window_is_not_a_modal(self):
        owner = _main(1, enabled=True)
        panel = _panel(2, "Preferences", 1)

        with fake_user32.install(unity_modal_blockers, [owner, panel]):
            self.assertFalse(unity_modal_blockers._is_modal_window(2))

    def test_panel_with_disabled_owner_is_not_a_modal(self):
        # Regression: owner-disabled alone is not sufficient. A non-blocking
        # Editor panel whose owner happens to be disabled must not be promoted,
        # or every panel becomes a blocker whenever any window disables it.
        owner = _main(1, enabled=False)
        panel = _panel(2, "Preferences", 1)

        with fake_user32.install(unity_modal_blockers, [owner, panel]):
            self.assertFalse(unity_modal_blockers._is_modal_window(2))
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(blockers, [])

    def test_owned_dialog_with_enabled_owner_is_not_a_modal(self):
        owner = _main(1, enabled=True)
        dialog = _dialog(2, "Owned Dialog", owner=1)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            self.assertFalse(unity_modal_blockers._is_modal_window(2))

    def test_ownerless_dialog_is_a_modal(self):
        dialog = _dialog(3, "Enter Safe Mode?", rect=(100, 100, 480, 260))

        with fake_user32.install(unity_modal_blockers, [dialog]):
            self.assertTrue(unity_modal_blockers._is_modal_window(3))

    def test_ownerless_large_window_is_not_a_modal(self):
        window = fake_user32.FakeWindow(4, title="Large Panel", style=fake_user32.WS_POPUP, rect=(0, 0, 1600, 1000))

        with fake_user32.install(unity_modal_blockers, [window]):
            self.assertFalse(unity_modal_blockers._is_modal_window(4))

    def test_non_blocking_editor_windows_are_never_promoted(self):
        owner = _main(1, enabled=True)
        panels = [
            _panel(2, "Preferences", 1),
            _panel(3, "Project Settings", 1),
            _panel(4, "Build Settings", 1),
            _panel(5, "About Unity", 1),
        ]

        with fake_user32.install(unity_modal_blockers, [owner] + panels):
            for panel in panels:
                self.assertFalse(
                    unity_modal_blockers._is_modal_window(panel.hwnd),
                    "{} must not be treated as blocking".format(panel.title),
                )
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(blockers, [])

    def test_unknown_window_failing_both_tests_is_downgraded(self):
        # Visible and titled, but neither owned-and-disabling nor dialog-sized.
        window = _dialog(6, "Mystery Window", style=0, rect=(0, 0, 1600, 1000))

        with fake_user32.install(unity_modal_blockers, [window]):
            self.assertFalse(unity_modal_blockers._is_modal_window(6))
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(blockers, [])


class UnknownDialogReportingTests(unittest.TestCase):
    """D3: unrecognized modals are reported rather than dropped."""

    def _unknown_setup(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Delete Asset?", owner=1, rect=(200, 200, 640, 380))
        dialog.with_children(
            _button(3, "&Delete"),
            _button(4, "Cancel"),
        )
        return owner, dialog

    def test_unknown_modal_dialog_is_reported(self):
        owner, dialog = self._unknown_setup()

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["type"], "unknown_modal_dialog")
        self.assertEqual(blockers[0]["scope"], "exec")
        self.assertEqual(blockers[0]["hwnd"], 2)
        self.assertEqual(blockers[0]["body"], "")

    def test_unknown_payload_carries_hwnd_title_body_and_buttons(self):
        owner, dialog = self._unknown_setup()

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            blocker = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")[0]

        self.assertEqual(blocker["hwnd"], 2)
        self.assertEqual(blocker["title"], "Delete Asset?")
        self.assertIn("body", blocker)
        self.assertEqual([b["label"] for b in blocker["buttons"]], ["&Delete", "Cancel"])

    def test_unknown_payload_has_no_known_or_default_button_field(self):
        owner, dialog = self._unknown_setup()

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            blocker = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")[0]

        self.assertNotIn("known", blocker)
        self.assertNotIn("default_button", blocker)
        for button in blocker["buttons"]:
            self.assertNotIn("is_default", button)

    def test_catalog_title_hit_reports_without_discrimination(self):
        # Owner enabled: this window would fail the modality test, but the
        # title is the existing contract, so it still reports.
        owner = _main(1, enabled=True)
        dialog = _dialog(2, "Save Scene", owner=1)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual([b["type"] for b in blockers], ["save_scene_dialog"])

    def test_api_updater_dialog_is_still_not_a_blocker(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Unity", owner=1)
        dialog.with_children(
            fake_user32.static_text(3, unity_modal_blockers.API_UPDATER_MESSAGE_FINGERPRINT)
        )

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(blockers, [])

    def test_unknown_dialog_sorts_ahead_of_catalog_dialogs(self):
        owner = _main(1, enabled=False)
        unknown = _dialog(2, "Delete Asset?", owner=1, rect=(200, 200, 640, 380))
        save_scene = _dialog(3, "Save Scene", owner=1)

        with fake_user32.install(unity_modal_blockers, [owner, unknown, save_scene]):
            blockers = unity_modal_blockers.list_supported_modal_blockers(4321, scope="exec")

        self.assertEqual(
            [b["type"] for b in blockers], ["unknown_modal_dialog", "save_scene_dialog"]
        )

    def test_detect_modal_blocker_returns_the_highest_priority_blocker(self):
        owner = _main(1, enabled=False)
        unknown = _dialog(2, "Delete Asset?", owner=1, rect=(200, 200, 640, 380))
        save_scene = _dialog(3, "Save Scene", owner=1)

        with fake_user32.install(unity_modal_blockers, [owner, unknown, save_scene]):
            blocker = unity_modal_blockers.detect_modal_blocker(4321, scope="exec")

        self.assertEqual(blocker["type"], "unknown_modal_dialog")


class ButtonEnumerationTests(unittest.TestCase):
    """D4: only clickable push buttons are candidates."""

    def _dialog_with(self, *children):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Options", owner=1)
        for child in children:
            dialog.with_children(child)
        return owner, dialog

    def test_enumerates_push_buttons_with_hwnd_label_and_ctrl_id(self):
        owner, dialog = self._dialog_with(_button(3, "&Save"), _button(4, "Cancel"))

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            buttons = unity_modal_blockers._enumerate_buttons(2)

        self.assertEqual([b["label"] for b in buttons], ["&Save", "Cancel"])
        for button in buttons:
            self.assertEqual(set(button), {"hwnd", "label", "ctrl_id"})

    def test_checkbox_and_radio_controls_are_excluded(self):
        checkbox = fake_user32.FakeWindow(
            3, title="Apply to all", class_name="Button", style=fake_user32._style(fake_user32.BS_CHECKBOX)
        )
        radio = fake_user32.FakeWindow(
            4, title="Overwrite", class_name="Button", style=fake_user32._style(fake_user32.BS_RADIOBUTTON)
        )
        push = _button(5, "OK")
        owner, dialog = self._dialog_with(checkbox, radio, push)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            buttons = unity_modal_blockers._enumerate_buttons(2)

        self.assertEqual([b["label"] for b in buttons], ["OK"])

    def test_group_box_is_excluded(self):
        group = fake_user32.FakeWindow(
            3, title="Options", class_name="Button", style=fake_user32._style(fake_user32.BS_GROUPBOX)
        )
        push = _button(4, "Save")
        owner, dialog = self._dialog_with(group, push)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            buttons = unity_modal_blockers._enumerate_buttons(2)

        self.assertEqual([b["label"] for b in buttons], ["Save"])

    def test_disabled_button_is_excluded(self):
        disabled = fake_user32.FakeWindow(
            3,
            title="Save",
            class_name="Button",
            style=fake_user32._style(0) | fake_user32.WS_DISABLED,
        )
        enabled = _button(4, "Cancel")
        owner, dialog = self._dialog_with(disabled, enabled)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            buttons = unity_modal_blockers._enumerate_buttons(2)

        self.assertEqual([b["label"] for b in buttons], ["Cancel"])

    def test_invisible_button_is_excluded(self):
        hidden = fake_user32.button(3, "Save")
        hidden.visible = False
        owner, dialog = self._dialog_with(hidden, _button(4, "Cancel"))

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            buttons = unity_modal_blockers._enumerate_buttons(2)

        self.assertEqual([b["label"] for b in buttons], ["Cancel"])


class ButtonLabelMatchingTests(unittest.TestCase):
    """D4: label matching strips mnemonics and is case-insensitive."""

    def setUp(self):
        self.buttons = [
            {"hwnd": 3, "label": "&Save", "ctrl_id": 3},
            {"hwnd": 4, "label": "Don't Save", "ctrl_id": 4},
        ]

    def test_mnemonic_is_stripped(self):
        matched = unity_modal_blockers._match_button(self.buttons, "Save")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["hwnd"], 3)

    def test_match_is_case_insensitive(self):
        matched = unity_modal_blockers._match_button(self.buttons, "save")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["hwnd"], 3)

    def test_whitespace_is_trimmed(self):
        matched = unity_modal_blockers._match_button(self.buttons, "  Save  ")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["hwnd"], 3)

    def test_label_with_apostrophe_matches(self):
        matched = unity_modal_blockers._match_button(self.buttons, "Don't Save")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["hwnd"], 4)

    def test_unknown_label_matches_nothing(self):
        self.assertIsNone(unity_modal_blockers._match_button(self.buttons, "Delete Everything"))

    def test_empty_label_matches_nothing(self):
        self.assertIsNone(unity_modal_blockers._match_button(self.buttons, ""))


class ClickChainTests(unittest.TestCase):
    """D5: message-level first, foreground last, Safe Mode exempt."""

    def test_message_level_click_does_not_foreground(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Delete Asset?", owner=1)
        button = _button(3, "&Delete")
        dialog.with_children(button)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            unity_modal_blockers._click_button(2, {"hwnd": 3, "label": "&Delete", "ctrl_id": 3})

        self.assertTrue(user32.called("SendMessageW"))
        self.assertFalse(user32.called("SetForegroundWindow"))

    def test_chain_escalates_when_first_level_does_not_close(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Delete Asset?", owner=1)
        dialog.with_children(_button(3, "&Delete"))

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            unity_modal_blockers._click_button(2, {"hwnd": 3, "label": "&Delete", "ctrl_id": 3})

        sends = [m for name, args in user32.calls if name == "SendMessageW" for m in [args[1]]]
        self.assertIn(unity_modal_blockers.BM_CLICK, sends)
        self.assertIn(unity_modal_blockers.WM_COMMAND, sends)
        self.assertTrue(user32.called("PostMessageW"))

    def test_chain_stops_early_when_dialog_closes(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Delete Asset?", owner=1)
        button = _button(3, "&Delete")
        dialog.auto_close = True
        dialog.with_children(button)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            unity_modal_blockers._click_button(2, {"hwnd": 3, "label": "&Delete", "ctrl_id": 3})

        sends = [m for name, args in user32.calls if name == "SendMessageW" for m in [args[1]]]
        self.assertEqual(sends, [unity_modal_blockers.BM_CLICK])
        self.assertFalse(user32.called("PostMessageW"))

    def test_safe_mode_uses_foreground_keyboard_path(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Enter Safe Mode?", owner=1)
        dialog.with_children(_button(3, "&Enter Safe Mode"))
        dialog.auto_close = True

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=2, button="Enter Safe Mode"
            )

        self.assertTrue(result["ok"])
        self.assertTrue(user32.called("SetForegroundWindow"))
        self.assertTrue(user32.called("keybd_event"))


class ResolveBlockerTests(unittest.TestCase):
    """D1: cancel is Safe-Mode-only; everything else resolves by named click."""

    def _scene(self, title="Save Scene", enabled_owner=False):
        owner = _main(1, enabled=enabled_owner)
        dialog = _dialog(2, title, owner=1)
        dialog.with_children(_button(3, "&Save"), _button(4, "Cancel"))
        return owner, dialog

    def test_cancel_on_save_scene_is_rejected(self):
        owner, dialog = self._scene()

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(4321, action="cancel")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "resolution_failed")
        self.assertEqual(result["error"], "action_not_supported_for_blocker")

    def test_cancel_does_not_activate_any_control(self):
        owner, dialog = self._scene()

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            unity_modal_blockers.resolve_modal_blocker(4321, action="cancel")

        self.assertFalse(user32.called("SendMessageW"))
        self.assertFalse(user32.called("keybd_event"))

    def test_cancel_on_safe_mode_is_allowed(self):
        owner = _main(1, enabled=False)
        dialog = _dialog(2, "Enter Safe Mode?", owner=1)
        dialog.with_children(_button(3, "&Enter Safe Mode"))
        dialog.auto_close = True

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(4321, action="cancel")

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["action"], "cancel")
        self.assertEqual(result["result"]["blocker"]["type"], "safe_mode_dialog")

    def test_click_resolves_a_save_scene_dialog(self):
        owner, dialog = self._scene(enabled_owner=True)
        dialog.auto_close = True

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=2, button="Cancel"
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["status"], "resolved")
        self.assertEqual(result["result"]["action"], "click")
        self.assertEqual(result["result"]["blocker"]["type"], "save_scene_dialog")

    def test_click_matches_label_without_mnemonic(self):
        owner, dialog = self._scene(enabled_owner=True)
        dialog.auto_close = True

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=2, button="save"
            )

        self.assertTrue(result["ok"])

    def test_click_with_unknown_hwnd_returns_window_not_found(self):
        owner, dialog = self._scene(enabled_owner=True)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=99, button="Cancel"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "window_not_found")
        self.assertFalse(user32.called("SendMessageW"))

    def test_click_with_unmatched_label_returns_button_not_found(self):
        owner, dialog = self._scene(enabled_owner=True)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]) as user32:
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=2, button="Delete Everything"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "button_not_found")
        self.assertFalse(user32.called("SendMessageW"))

    def test_click_without_hwnd_or_button_is_rejected(self):
        owner, dialog = self._scene(enabled_owner=True)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(4321, action="click")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "button_not_found")

    def test_click_targets_explicit_window_despite_multiple_blockers(self):
        owner = _main(1, enabled=False)
        first = _dialog(2, "Delete Asset?", owner=1)
        first.with_children(_button(3, "&Delete"))
        second = _dialog(4, "Save Scene", owner=1)
        second.auto_close = True
        second.with_children(_button(5, "Cancel"))

        with fake_user32.install(unity_modal_blockers, [owner, first, second]):
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=4, button="Cancel"
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["blocker"]["type"], "save_scene_dialog")

    def test_click_reports_failure_when_dialog_does_not_close(self):
        owner, dialog = self._scene(enabled_owner=True)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="click", hwnd=2, button="Cancel", timeout_ms=1, poll_interval_ms=1
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "click_not_confirmed")

    def test_cancel_with_hwnd_is_rejected(self):
        owner, dialog = self._scene(enabled_owner=True)

        with fake_user32.install(unity_modal_blockers, [owner, dialog]):
            result = unity_modal_blockers.resolve_modal_blocker(
                4321, action="cancel", hwnd=2, button="Cancel"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "action_not_supported_for_blocker")


class DismissApiUpdaterDialogTests(unittest.TestCase):
    def _run(self, states, click_result=True):
        clock = _FakeClock()
        cursor = {"index": 0}
        clicked = []

        def list_fn(_pid):
            index = min(cursor["index"], len(states) - 1)
            result = states[index]
            cursor["index"] += 1
            return result

        def click_fn(dialog):
            clicked.append(dialog["hwnd"])
            return click_result

        result = unity_modal_blockers.dismiss_api_updater_dialog(
            4321,
            timeout_ms=2000,
            poll_interval_ms=100,
            list_dialogs_fn=list_fn,
            click_fn=click_fn,
            time_ref=clock,
        )
        return result, clicked

    def test_two_sequential_dialogs_record_two_declines(self):
        with mock.patch.object(unity_modal_blockers.sys, "platform", "win32"):
            result, clicked = self._run(
                [
                    [{"hwnd": 1, "type": unity_modal_blockers.API_UPDATER_DIALOG_TYPE}],
                    [{"hwnd": 2, "type": unity_modal_blockers.API_UPDATER_DIALOG_TYPE}],
                    [],
                ]
            )

        self.assertEqual(result["dismissed"], 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "dismissed")
        self.assertEqual(clicked, [1, 2])

    def test_no_dialog_is_a_no_op(self):
        with mock.patch.object(unity_modal_blockers.sys, "platform", "win32"):
            result, clicked = self._run([[]])

        self.assertEqual(result["dismissed"], 0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "no_dialog")
        self.assertEqual(clicked, [])

    def test_failed_click_stops_without_claiming_a_decline(self):
        with mock.patch.object(unity_modal_blockers.sys, "platform", "win32"):
            result, clicked = self._run(
                [[{"hwnd": 1, "type": unity_modal_blockers.API_UPDATER_DIALOG_TYPE}]],
                click_result=False,
            )

        self.assertEqual(result["dismissed"], 0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "click_failed")
        self.assertEqual(clicked, [1])

    def test_non_windows_is_unsupported(self):
        with mock.patch.object(unity_modal_blockers.sys, "platform", "linux"):
            result = unity_modal_blockers.dismiss_api_updater_dialog(4321)

        self.assertEqual(result["dismissed"], 0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
