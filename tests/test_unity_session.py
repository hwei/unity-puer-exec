import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_session  # type: ignore


SAMPLE_PROJECT_PATH = "X:/unity-project"


def _make_session():
    return unity_session.UnitySession(
        owner="test",
        base_url="http://127.0.0.1:55231",
        project_path=SAMPLE_PROJECT_PATH,
    )


def _require_test_project_path():
    # This test intentionally exercises the repo-level runtime resolution path,
    # so it loads .env before checking the process environment.
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

    def test_resolve_effective_log_path_prefers_session_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            unity_session.write_session_artifact(
                project_path,
                {
                    "base_url": "http://127.0.0.1:55231",
                    "unity_pid": 1234,
                    "session_marker": "marker-1",
                    "effective_log_path": "X:/artifact/Editor.log",
                },
            )
            with mock.patch.object(unity_session, "_is_pid_running", return_value=True):
                resolved = unity_session._resolve_effective_log_path(project_path, unity_log_path="X:/explicit/Editor.log")

        self.assertEqual(resolved, Path("X:/artifact/Editor.log"))

    def test_resolve_effective_log_path_uses_explicit_path_before_session_marker_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            unity_session.write_session_artifact(
                project_path,
                {
                    "base_url": "http://127.0.0.1:55231",
                    "unity_pid": 1234,
                    "effective_log_path": "X:/artifact/Editor.log",
                },
            )

            resolved = unity_session._resolve_effective_log_path(project_path, unity_log_path="X:/explicit/Editor.log")

        self.assertEqual(resolved, Path("X:/explicit/Editor.log"))

    def test_create_observation_session_uses_explicit_log_path_before_session_marker_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            with mock.patch.object(unity_session, "_list_unity_pids", return_value=[]):
                session = unity_session.create_observation_session(project_path=project_path, unity_log_path="X:/custom/Editor.log")

        self.assertIsNotNone(session)
        self.assertEqual(Path(session.effective_log_path), Path("X:/custom/Editor.log"))
        self.assertEqual(session.owner, "observation")

    def test_create_observation_session_prefers_artifact_path_after_session_marker_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            unity_session.write_session_artifact(
                project_path,
                {
                    "base_url": "http://127.0.0.1:55231",
                    "unity_pid": 1234,
                    "session_marker": "marker-1",
                    "effective_log_path": "X:/artifact/Editor.log",
                },
            )
            with mock.patch.object(unity_session, "_is_pid_running", return_value=True):
                session = unity_session.create_observation_session(
                    project_path=project_path,
                    unity_log_path="X:/explicit/Editor.log",
                )

        self.assertEqual(Path(session.effective_log_path), Path("X:/artifact/Editor.log"))
        self.assertEqual(session.owner, "session_artifact")

    def test_resolve_effective_log_path_ignores_stale_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            unity_session.write_session_artifact(
                project_path,
                {
                    "base_url": "http://127.0.0.1:55231",
                    "unity_pid": 1234,
                    "session_marker": "marker-1",
                    "effective_log_path": "X:/artifact/Editor.log",
                },
            )
            with mock.patch.object(unity_session, "_is_pid_running", return_value=False):
                resolved = unity_session._resolve_effective_log_path(project_path, unity_log_path="X:/explicit/Editor.log")

        self.assertEqual(resolved, Path("X:/explicit/Editor.log"))

    def test_persist_ready_session_artifact_requires_session_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            session = unity_session.UnitySession(
                owner="test",
                base_url="http://127.0.0.1:55231",
                project_path=project_path,
                unity_pid=1234,
            )
            unity_session._persist_ready_session_artifact(session, Path("X:/artifact/Editor.log"))

            artifact = unity_session.read_session_artifact(project_path)

        self.assertIsNone(artifact)

    def test_persist_ready_session_artifact_writes_effective_log_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            session = unity_session.UnitySession(
                owner="test",
                base_url="http://127.0.0.1:55231",
                project_path=project_path,
                unity_pid=1234,
            )
            session.diagnostics["last_health_payload"] = {"session_marker": "marker-1"}

            unity_session._persist_ready_session_artifact(session, Path("X:/artifact/Editor.log"))
            artifact = unity_session.read_session_artifact(project_path)

        self.assertEqual(artifact["session_marker"], "marker-1")
        self.assertEqual(Path(artifact["effective_log_path"]), Path("X:/artifact/Editor.log"))

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

    def test_ensure_session_ready_reuses_project_recovery_without_launching(self):
        recovered = unity_session.UnitySession(
            owner="project_recovery",
            base_url="http://127.0.0.1:55231",
            project_path=SAMPLE_PROJECT_PATH,
            unity_pid=4321,
        )

        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=None
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", return_value=[4321]
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", return_value={"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True}
        ), mock.patch.object(
            unity_session, "read_launch_claim", return_value=None
        ), mock.patch.object(
            unity_session, "wait_ready_with_activity", return_value=recovered
        ) as wait_ready_with_activity, mock.patch.object(
            unity_session, "_launch_unity"
        ) as launch_unity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ):
            result = unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertIs(result, recovered)
        launch_unity.assert_not_called()
        wait_ready_with_activity.assert_called_once()
        persist_ready.assert_called_once_with(recovered, Path("X:/Logs/Editor.log"))

    def test_ensure_session_ready_raises_launch_conflict_for_active_other_claim(self):
        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=None
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", return_value=[]
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", return_value={"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False}
        ), mock.patch.object(
            unity_session, "read_launch_claim", return_value={"owner_pid": 2222, "created_at": 10.0}
        ), mock.patch.object(
            unity_session, "_is_pid_running", side_effect=lambda pid: pid == 2222
        ):
            with self.assertRaises(unity_session.UnityLaunchConflictError) as ctx:
                unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertEqual(ctx.exception.session.owner, "launch_conflict")
        self.assertEqual(ctx.exception.session.diagnostics["launch_conflict_reason"], "project_launch_claim_active")

    def test_ensure_session_ready_rechecks_after_claim_before_launching(self):
        recovered = unity_session.UnitySession(
            owner="session_artifact",
            base_url="http://127.0.0.1:55231",
            project_path=SAMPLE_PROJECT_PATH,
            unity_pid=9999,
        )
        session_artifact = {"unity_pid": 9999}

        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=session_artifact
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", side_effect=[[], [9999], [9999]]
        ), mock.patch.object(
            unity_session, "_probe_health", side_effect=[(None, "connection refused"), (None, "still starting")]
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
            ]
        ), mock.patch.object(
            unity_session, "read_launch_claim", side_effect=[None, {"owner_pid": 1111}, {"owner_pid": 1111}]
        ), mock.patch.object(
            unity_session, "write_launch_claim"
        ) as write_launch_claim, mock.patch.object(
            unity_session, "clear_launch_claim"
        ) as clear_launch_claim, mock.patch.object(
            unity_session, "_is_pid_running", side_effect=[False, True, True]
        ), mock.patch.object(
            unity_session, "wait_ready_with_activity", return_value=recovered
        ) as wait_ready_with_activity, mock.patch.object(
            unity_session, "_launch_unity"
        ) as launch_unity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ):
            with mock.patch.object(unity_session.os, "getpid", return_value=1111):
                result = unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertIs(result, recovered)
        write_launch_claim.assert_called_once()
        clear_launch_claim.assert_called_once_with(Path(SAMPLE_PROJECT_PATH))
        launch_unity.assert_not_called()
        wait_ready_with_activity.assert_called_once()
        persist_ready.assert_called_once_with(recovered, Path("X:/Logs/Editor.log"))

    def test_ensure_session_ready_recovers_when_launched_process_exits_cleanly_before_ready(self):
        recovered = unity_session.UnitySession(
            owner="project_recovery",
            base_url="http://127.0.0.1:55231",
            project_path=SAMPLE_PROJECT_PATH,
            unity_pid=7777,
        )
        
        def fake_wait(session, *args, **kwargs):
            if session.owner == "launched":
                session.process.returncode = 0
                raise unity_session.UnityLaunchError("Unity exited before ready with code 0", session=session)
            return recovered

        process = mock.Mock(pid=5555)
        session_artifact = {"unity_pid": 7777}

        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=session_artifact
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", side_effect=[[], [], [7777], [7777], [7777]]
        ), mock.patch.object(
            unity_session, "_probe_health", side_effect=[(None, "connection refused"), (None, "still starting"), (None, "handoff")]
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
            ]
        ), mock.patch.object(
            unity_session, "read_launch_claim", side_effect=[None, {"owner_pid": 1111}, {"owner_pid": 1111}]
        ), mock.patch.object(
            unity_session, "write_launch_claim"
        ), mock.patch.object(
            unity_session, "clear_launch_claim"
        ), mock.patch.object(
            unity_session, "_is_pid_running", side_effect=[False, False, True, True]
        ), mock.patch.object(
            unity_session, "_resolve_unity_exe_path", return_value="X:/Unity/Unity.exe"
        ), mock.patch.object(
            unity_session, "_launch_unity", return_value=process
        ), mock.patch.object(
            unity_session, "wait_ready_with_activity", side_effect=fake_wait
        ) as wait_ready_with_activity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ):
            with mock.patch.object(unity_session.os, "getpid", return_value=1111):
                result = unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertIs(result, recovered)
        self.assertEqual(wait_ready_with_activity.call_count, 2)
        persist_ready.assert_called_once_with(recovered, Path("X:/Logs/Editor.log"))

    def test_detach_session_process_clears_live_process_handle(self):
        session = _make_session()
        process = mock.Mock()
        process.returncode = None
        session.process = process

        result = unity_session._detach_session_process(session)

        self.assertIs(result, session)
        self.assertIsNone(session.process)
        self.assertEqual(process.returncode, 0)


if __name__ == "__main__":
    unittest.main()
