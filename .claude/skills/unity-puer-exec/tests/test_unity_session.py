import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

import unity_session  # type: ignore


class UnitySessionTests(unittest.TestCase):
    def test_wait_until_healthy_returns_session_when_ready(self):
        session = unity_session.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="F:/C3/c3-client-tree2/Project",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("boot\n", encoding="utf-8")

            with mock.patch.object(
                unity_session,
                "_probe_health",
                side_effect=[
                    ({"ok": False, "status": "compiling"}, None),
                    ({"ok": True, "status": "ready"}, None),
                ],
            ), mock.patch.object(
                unity_session,
                "_list_unity_pids",
                return_value=[1234],
            ), mock.patch.object(
                unity_session.time,
                "sleep",
                return_value=None,
            ):
                result = unity_session.wait_until_healthy(
                    session,
                    timeout_seconds=5.0,
                    activity_timeout_seconds=10.0,
                    log_path=log_path,
                )

        self.assertIs(result, session)
        self.assertEqual(session.diagnostics["last_health_payload"]["status"], "ready")
        self.assertEqual(session.diagnostics["editor_log_exists"], True)

    def test_wait_until_healthy_stalls_when_log_has_no_activity(self):
        session = unity_session.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="F:/C3/c3-client-tree2/Project",
        )

        time_values = iter([0.0, 0.0, 0.0, 20.0, 20.0, 20.0, 20.0])

        def fake_time():
            return next(time_values)

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("boot\n", encoding="utf-8")

            with mock.patch.object(
                unity_session,
                "_probe_health",
                return_value=({"ok": False, "status": "compiling"}, None),
            ), mock.patch.object(
                unity_session,
                "_list_unity_pids",
                return_value=[1234],
            ), mock.patch.object(
                unity_session.time,
                "time",
                side_effect=fake_time,
            ), mock.patch.object(
                unity_session.time,
                "sleep",
                return_value=None,
            ):
                with self.assertRaises(unity_session.UnityStalledError) as ctx:
                    unity_session.wait_until_healthy(
                        session,
                        timeout_seconds=60.0,
                        activity_timeout_seconds=10.0,
                        log_path=log_path,
                    )

        self.assertEqual(ctx.exception.session, session)
        self.assertEqual(session.diagnostics["last_health_payload"]["status"], "compiling")
        self.assertGreaterEqual(session.diagnostics["idle_seconds"], 10.0)

    def test_wait_for_log_pattern_matches_new_output(self):
        session = unity_session.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="F:/C3/c3-client-tree2/Project",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("existing\n", encoding="utf-8")

            def fake_sleep(_seconds):
                log_path.write_text("existing\n[Build] complete\n", encoding="utf-8")

            with mock.patch.object(
                unity_session,
                "_probe_health",
                return_value=({"ok": False, "status": "compiling"}, None),
            ), mock.patch.object(
                unity_session,
                "_list_unity_pids",
                return_value=[1234],
            ), mock.patch.object(
                unity_session.time,
                "sleep",
                side_effect=fake_sleep,
            ):
                result = unity_session.wait_for_log_pattern(
                    session,
                    r"\[Build\] complete",
                    timeout_seconds=5.0,
                    activity_timeout_seconds=10.0,
                    log_path=log_path,
                )

        self.assertIs(result, session)
        self.assertEqual(session.diagnostics["matched_log_text"], "[Build] complete")
        self.assertEqual(session.diagnostics["matched_log_pattern"], r"\[Build\] complete")

    def test_wait_until_recovered_records_health_transitions(self):
        session = unity_session.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="F:/C3/c3-client-tree2/Project",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("boot\ncompiling\nready\n", encoding="utf-8")

            with mock.patch.object(
                unity_session,
                "_probe_health",
                side_effect=[
                    ({"ok": False, "status": "compiling"}, None),
                    ({"ok": True, "status": "ready", "port": 55231}, None),
                ],
            ), mock.patch.object(
                unity_session,
                "_list_unity_pids",
                return_value=[1234],
            ), mock.patch.object(
                unity_session.time,
                "sleep",
                return_value=None,
            ):
                result = unity_session.wait_until_recovered(
                    session,
                    timeout_seconds=5.0,
                    activity_timeout_seconds=10.0,
                    log_path=log_path,
                )

        self.assertIs(result, session)
        self.assertEqual(session.diagnostics["wait_kind"], "recovery")
        self.assertEqual(
            session.diagnostics["observed_health"],
            [
                {"ok": False, "status": "compiling"},
                {"ok": True, "status": "ready", "port": 55231},
            ],
        )
        self.assertEqual(session.diagnostics["recovery_observed"], True)
        self.assertEqual(session.diagnostics["recovery_not_needed"], False)

    def test_wait_until_recovered_marks_recovery_not_needed_when_already_ready(self):
        session = unity_session.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="F:/C3/c3-client-tree2/Project",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("ready\n", encoding="utf-8")

            with mock.patch.object(
                unity_session,
                "_probe_health",
                return_value=({"ok": True, "status": "ready", "port": 55231}, None),
            ), mock.patch.object(
                unity_session,
                "_list_unity_pids",
                return_value=[1234],
            ), mock.patch.object(
                unity_session.time,
                "sleep",
                return_value=None,
            ):
                result = unity_session.wait_until_recovered(
                    session,
                    timeout_seconds=5.0,
                    activity_timeout_seconds=10.0,
                    log_path=log_path,
                )

        self.assertIs(result, session)
        self.assertEqual(session.diagnostics["observed_health"], [{"ok": True, "status": "ready", "port": 55231}])
        self.assertEqual(session.diagnostics["recovery_observed"], False)
        self.assertEqual(session.diagnostics["recovery_not_needed"], True)


if __name__ == "__main__":
    unittest.main()
