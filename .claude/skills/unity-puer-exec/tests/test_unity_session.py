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


SAMPLE_PROJECT_PATH = "X:/unity-project"


def _make_session():
    return unity_session.UnitySession(
        owner="test",
        base_url="http://127.0.0.1:55231",
        project_path=SAMPLE_PROJECT_PATH,
    )


def _require_test_project_path():
    unity_session._ensure_dotenv_loaded(force=True)
    project_path = os.environ.get(unity_session.UNITY_PROJECT_PATH_ENV)
    if not project_path:
        raise AssertionError(
            "{} must be set before running tests that require a real Unity project path.".format(
                unity_session.UNITY_PROJECT_PATH_ENV
            )
        )
    return Path(project_path)


class UnitySessionTests(unittest.TestCase):
    def test_resolve_project_path_prefers_explicit_argument(self):
        with mock.patch.dict(os.environ, {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-env"}, clear=False):
            resolved = unity_session.resolve_project_path("X:/from-arg", cwd="X:/from-cwd")

        self.assertEqual(resolved, Path("X:/from-arg"))

    def test_load_dotenv_file_ignores_comments_and_blank_lines(self):
        env = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "# comment\n\nUNITY_PROJECT_PATH=X:/from-dotenv\nIGNORED_VALUE = value\n",
                encoding="utf-8",
            )
            loaded = unity_session._load_dotenv_file(dotenv_path, env=env)

        self.assertEqual(loaded, True)
        self.assertEqual(env[unity_session.UNITY_PROJECT_PATH_ENV], "X:/from-dotenv")
        self.assertEqual(env["IGNORED_VALUE"], "value")

    def test_load_dotenv_file_does_not_override_existing_environment(self):
        env = {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-process-env"}
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text("UNITY_PROJECT_PATH=X:/from-dotenv\n", encoding="utf-8")
            unity_session._load_dotenv_file(dotenv_path, env=env)

        self.assertEqual(env[unity_session.UNITY_PROJECT_PATH_ENV], "X:/from-process-env")

    def test_ensure_dotenv_loaded_returns_false_when_file_is_missing(self):
        env = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            loaded = unity_session._ensure_dotenv_loaded(env=env, dotenv_path=dotenv_path, force=True)

        self.assertEqual(loaded, False)
        self.assertEqual(env, {})

    def test_resolve_project_path_uses_environment_variable(self):
        with mock.patch.dict(os.environ, {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-env"}, clear=False):
            resolved = unity_session.resolve_project_path(None, cwd="X:/from-cwd")

        self.assertEqual(resolved, Path("X:/from-env"))

    def test_resolve_project_path_falls_back_to_cwd(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            unity_session,
            "_ensure_dotenv_loaded",
            return_value=False,
        ):
            resolved = unity_session.resolve_project_path(None, cwd="X:/from-cwd")

        self.assertEqual(resolved, Path("X:/from-cwd"))

    def test_resolve_project_path_uses_dotenv_path_when_requested(self):
        env = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text("UNITY_PROJECT_PATH=X:/from-dotenv\n", encoding="utf-8")
            unity_session._ensure_dotenv_loaded(env=env, dotenv_path=dotenv_path, force=True)
            resolved = unity_session.resolve_project_path(None, cwd="X:/from-cwd", env=env)

        self.assertEqual(resolved, Path("X:/from-dotenv"))

    def test_get_unity_version_reads_real_project_from_environment(self):
        project_path = _require_test_project_path()
        version = unity_session._get_unity_version(project_path)
        self.assertTrue(version)

    def test_wait_until_healthy_returns_session_when_ready(self):
        session = _make_session()

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
        session = _make_session()
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
        session = _make_session()

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
        session = _make_session()

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
        session = _make_session()

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
