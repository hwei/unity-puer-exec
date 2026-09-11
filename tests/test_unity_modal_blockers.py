import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

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
