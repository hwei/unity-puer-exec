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

    def test_get_unity_version_reads_project_version_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            project_version_path = project_path / "ProjectSettings" / "ProjectVersion.txt"
            project_version_path.parent.mkdir(parents=True, exist_ok=True)
            project_version_path.write_text(
                "m_EditorVersion: 2022.3.62f2\n",
                encoding="utf-8",
            )

            version = unity_session._get_unity_version(project_path)

        self.assertEqual(version, "2022.3.62f2")

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
            unity_session, "_project_lockfile_is_held", return_value=True
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

    def test_ensure_session_ready_launches_when_lock_is_fresh_but_no_editor_is_recoverable(self):
        launched = unity_session.UnitySession(
            owner="launched",
            base_url="http://127.0.0.1:55231",
            project_path=SAMPLE_PROJECT_PATH,
            unity_pid=5555,
            launched=True,
        )
        process = mock.Mock(pid=5555)

        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=None
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", return_value=[]
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
            ]
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=False
        ), mock.patch.object(
            unity_session, "read_launch_claim", side_effect=[None, {"owner_pid": 1111}, {"owner_pid": 1111}]
        ), mock.patch.object(
            unity_session, "write_launch_claim"
        ) as write_launch_claim, mock.patch.object(
            unity_session, "clear_launch_claim"
        ) as clear_launch_claim, mock.patch.object(
            unity_session, "_is_pid_running", return_value=False
        ), mock.patch.object(
            unity_session, "_resolve_unity_exe_path", return_value="X:/Unity/Unity.exe"
        ), mock.patch.object(
            unity_session, "_launch_unity", return_value=process
        ) as launch_unity, mock.patch.object(
            unity_session, "wait_ready_with_activity", return_value=launched
        ) as wait_ready_with_activity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ):
            with mock.patch.object(unity_session.os, "getpid", return_value=1111):
                result = unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertIs(result, launched)
        write_launch_claim.assert_called_once()
        clear_launch_claim.assert_called_once_with(Path(SAMPLE_PROJECT_PATH))
        launch_unity.assert_called_once_with(Path(SAMPLE_PROJECT_PATH), "X:/Unity/Unity.exe", unity_log_path=None)
        wait_ready_with_activity.assert_called_once()
        self.assertEqual(wait_ready_with_activity.call_args.args[0].owner, "launched")
        persist_ready.assert_called_once_with(launched, Path("X:/Logs/Editor.log"))

    def test_ensure_session_ready_launches_when_unrelated_project_running_but_own_lock_is_free(self):
        # Regression for the project-scoped-recovery-signal defect: an unrelated
        # project's Editor is running on the host (non-empty unity_pids), but the
        # requested project has no session artifact and its own lockfile is free.
        # ensure_session_ready must launch the requested project instead of
        # entering a recovery wait for a recovery that will never happen.
        launched = unity_session.UnitySession(
            owner="launched",
            base_url="http://127.0.0.1:55231",
            project_path=SAMPLE_PROJECT_PATH,
            unity_pid=6666,
            launched=True,
        )
        process = mock.Mock(pid=6666)

        with mock.patch.object(unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)), mock.patch.object(
            unity_session, "read_session_artifact", return_value=None
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_list_unity_pids", return_value=[9001]
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
            ]
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=False
        ), mock.patch.object(
            unity_session, "read_launch_claim", side_effect=[None, {"owner_pid": 1111}, {"owner_pid": 1111}]
        ), mock.patch.object(
            unity_session, "write_launch_claim"
        ) as write_launch_claim, mock.patch.object(
            unity_session, "clear_launch_claim"
        ) as clear_launch_claim, mock.patch.object(
            unity_session, "_is_pid_running", return_value=False
        ), mock.patch.object(
            unity_session, "_resolve_unity_exe_path", return_value="X:/Unity/Unity.exe"
        ), mock.patch.object(
            unity_session, "_launch_unity", return_value=process
        ) as launch_unity, mock.patch.object(
            unity_session, "wait_ready_with_activity", return_value=launched
        ) as wait_ready_with_activity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ):
            with mock.patch.object(unity_session.os, "getpid", return_value=1111):
                result = unity_session.ensure_session_ready(project_path=SAMPLE_PROJECT_PATH)

        self.assertIs(result, launched)
        write_launch_claim.assert_called_once()
        clear_launch_claim.assert_called_once_with(Path(SAMPLE_PROJECT_PATH))
        launch_unity.assert_called_once_with(Path(SAMPLE_PROJECT_PATH), "X:/Unity/Unity.exe", unity_log_path=None)
        wait_ready_with_activity.assert_called_once()
        persist_ready.assert_called_once_with(launched, Path("X:/Logs/Editor.log"))

    def test_ensure_session_ready_waits_when_own_lockfile_is_held_with_no_artifact_pid(self):
        # The requested project's own lockfile is held (an Editor for that exact
        # project is starting or open, not yet exposing a matched /health
        # response), but there is no session artifact pid. This must still be
        # treated as recoverable rather than attempting a duplicate launch that
        # would conflict with Unity's own project-lock enforcement.
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
            unity_session, "_list_unity_pids", return_value=[]
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", return_value={"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True}
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=True
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
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
            ]
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=False
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
            unity_session, "_probe_health", return_value=(None, "connection refused")
        ), mock.patch.object(
            unity_session, "_project_lock_details", side_effect=[
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False},
                {"path": "X:/unity-project/Temp/UnityLockfile", "exists": True, "fresh": True},
            ]
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=False
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


def _ready_payload(project_path):
    return {"ok": True, "status": "ready", "project_path": str(project_path)}


def _probe_by_url(mapping, default=(None, "connection refused")):
    """Build a _probe_health side_effect keyed by base_url.

    mapping: {base_url: (payload, error)}. Unlisted URLs return ``default``.
    """

    def probe(base_url, _timeout):
        return mapping.get(base_url, default)

    return probe


class RangeAwareDiscoveryTests(unittest.TestCase):
    PREFERRED = "http://127.0.0.1:55231"
    ROLLED_OVER = "http://127.0.0.1:55233"

    def test_discover_project_endpoint_hits_preferred_port_first(self):
        probe = mock.Mock(side_effect=_probe_by_url({self.PREFERRED: (_ready_payload(SAMPLE_PROJECT_PATH), None)}))
        with mock.patch.object(unity_session, "_probe_health", probe):
            base_url, payload, error, saw_other = unity_session.discover_project_endpoint(SAMPLE_PROJECT_PATH)

        self.assertEqual(base_url, self.PREFERRED)
        self.assertEqual(payload["project_path"], SAMPLE_PROJECT_PATH)
        self.assertIsNone(error)
        self.assertFalse(saw_other)
        # Short-circuits on the first candidate; no extra probes.
        self.assertEqual(probe.call_count, 1)

    def test_discover_project_endpoint_matches_non_preferred_port(self):
        probe = mock.Mock(side_effect=_probe_by_url({
            self.PREFERRED: (_ready_payload("X:/other-project"), None),
            self.ROLLED_OVER: (_ready_payload(SAMPLE_PROJECT_PATH), None),
        }))
        with mock.patch.object(unity_session, "_probe_health", probe):
            base_url, payload, error, saw_other = unity_session.discover_project_endpoint(SAMPLE_PROJECT_PATH)

        self.assertEqual(base_url, self.ROLLED_OVER)
        self.assertEqual(payload["project_path"], SAMPLE_PROJECT_PATH)
        self.assertTrue(saw_other)

    def test_discover_project_endpoint_skips_other_project_endpoints(self):
        probe = mock.Mock(side_effect=_probe_by_url({
            self.PREFERRED: (_ready_payload("X:/other-project"), None),
        }))
        with mock.patch.object(unity_session, "_probe_health", probe):
            base_url, payload, error, saw_other = unity_session.discover_project_endpoint(SAMPLE_PROJECT_PATH)

        self.assertIsNone(base_url)
        self.assertIsNone(payload)
        self.assertTrue(saw_other)

    def test_discover_project_endpoint_reports_no_match_when_nothing_reachable(self):
        probe = mock.Mock(return_value=(None, "connection refused"))
        with mock.patch.object(unity_session, "_probe_health", probe):
            base_url, payload, error, saw_other = unity_session.discover_project_endpoint(SAMPLE_PROJECT_PATH)

        self.assertIsNone(base_url)
        self.assertIsNone(payload)
        self.assertEqual(error, "connection refused")
        self.assertFalse(saw_other)
        # The full range was scanned when nothing matched.
        self.assertEqual(probe.call_count, len(unity_session.direct_exec_client.control_port_candidates()))

    def test_recovery_resolver_locks_onto_non_preferred_bound_port(self):
        # A starting/compiling Editor for our project is bound on a non-preferred port.
        compiling = {"ok": True, "status": "compiling", "project_path": SAMPLE_PROJECT_PATH}
        probe = mock.Mock(side_effect=_probe_by_url({self.ROLLED_OVER: (compiling, None)}))
        with mock.patch.object(unity_session, "_probe_health", probe):
            resolve = unity_session._make_recovery_endpoint_resolver(SAMPLE_PROJECT_PATH, 1.0)
            first = resolve()
            calls_after_scan = probe.call_count
            second = resolve()

        self.assertEqual(first, self.ROLLED_OVER)
        self.assertEqual(second, self.ROLLED_OVER)
        # Once locked, the resolver re-probes only the locked port instead of re-scanning.
        self.assertEqual(probe.call_count - calls_after_scan, 1)

    def test_recovery_resolver_returns_none_until_project_endpoint_appears(self):
        probe = mock.Mock(return_value=(None, "connection refused"))
        with mock.patch.object(unity_session, "_probe_health", probe):
            resolve = unity_session._make_recovery_endpoint_resolver(SAMPLE_PROJECT_PATH, 1.0)
            self.assertIsNone(resolve())

    def test_scan_any_status_finds_rolled_over_cold_start_editor(self):
        # Cold-start launch rolled over off the preferred port; Editor is still compiling.
        compiling = {"ok": True, "status": "compiling", "project_path": SAMPLE_PROJECT_PATH}
        other = _ready_payload("X:/other-project")
        probe = mock.Mock(side_effect=_probe_by_url({
            self.PREFERRED: (other, None),
            self.ROLLED_OVER: (compiling, None),
        }))
        with mock.patch.object(unity_session, "_probe_health", probe):
            found = unity_session._scan_for_project_endpoint_any_status(SAMPLE_PROJECT_PATH, 1.0)

        self.assertEqual(found, self.ROLLED_OVER)


class ExecEndpointMisrouteRegressionTests(unittest.TestCase):
    """Regression for the observed real-host exec misroute.

    Real-host validation (see
    openspec/changes/archive/2026-07-21-improve-large-response-retrieval/results/validation-evidence.md)
    observed `exec --project-path <tree2>` complete against an unrelated
    project's already-ready Editor on the preferred port while tree2 had no
    session artifact and was never launched. These tests exercise the real
    `wait_for_session` loop (not mocked, unlike the other `ensure_session_ready`
    tests in this module) because the defect lived specifically in that loop's
    fallback probe of a stale `session.base_url`.

    `project-scoped-recovery-signal` changed what happens next for this exact
    scenario: an unrelated project's pid alone no longer reads as "recoverable",
    so `ensure_session_ready` now proceeds to launch the requested project
    instead of entering a recovery wait that can never succeed. The real
    `wait_for_session` loop is still exercised here, just reached via the
    launched-session path rather than the pre-launch recovery path — the
    stale-`base_url` fallback probe this class guards against lives in that
    same shared loop either way.
    """

    PREFERRED = "http://127.0.0.1:55231"

    def test_ensure_session_ready_never_claims_unrelated_ready_project_on_preferred_port(self):
        other_project_payload = {
            "ok": True,
            "status": "ready",
            "project_path": "X:/other-project",
            "session_marker": "OTHER-PROJECT-MARKER",
        }

        def probe(base_url, _timeout):
            if base_url == self.PREFERRED:
                return other_project_payload, None
            return None, "connection refused"

        process = mock.Mock(pid=8765, returncode=None)
        process.poll.return_value = None

        with mock.patch.object(
            unity_session, "resolve_project_path", return_value=Path(SAMPLE_PROJECT_PATH)
        ), mock.patch.object(
            unity_session, "read_session_artifact", return_value=None
        ), mock.patch.object(
            unity_session, "_resolve_effective_log_path", return_value=Path("X:/Logs/Editor.log")
        ), mock.patch.object(
            unity_session, "_read_editor_log_size", return_value=0
        ), mock.patch.object(
            unity_session, "_read_recent_editor_log_lines", return_value=[]
        ), mock.patch.object(
            # An unrelated project's Editor is already running on the host; the
            # requested project's own Editor is not (no session artifact, own
            # lockfile not held) -> the fix now launches instead of waiting.
            unity_session, "_list_unity_pids", return_value=[57896]
        ), mock.patch.object(
            unity_session, "_probe_health", side_effect=probe
        ), mock.patch.object(
            unity_session, "_project_lock_details", return_value={
                "path": "X:/unity-project/Temp/UnityLockfile", "exists": False, "fresh": False,
            }
        ), mock.patch.object(
            unity_session, "_project_lockfile_is_held", return_value=False
        ), mock.patch.object(
            unity_session, "read_launch_claim", return_value=None
        ), mock.patch.object(
            unity_session, "write_launch_claim"
        ), mock.patch.object(
            unity_session, "clear_launch_claim"
        ), mock.patch.object(
            unity_session, "_is_pid_running", return_value=False
        ), mock.patch.object(
            unity_session, "_resolve_unity_exe_path", return_value="X:/Unity/Unity.exe"
        ), mock.patch.object(
            unity_session, "_launch_unity", return_value=process
        ) as launch_unity, mock.patch.object(
            unity_session, "_persist_ready_session_artifact"
        ) as persist_ready, mock.patch.object(
            unity_session, "_detach_session_process", side_effect=lambda session: session
        ), mock.patch.object(unity_session.time, "sleep"):
            with mock.patch.object(unity_session.os, "getpid", return_value=1111):
                with self.assertRaises(unity_session.UnityNotReadyError):
                    unity_session.ensure_session_ready(
                        project_path=SAMPLE_PROJECT_PATH, ready_timeout_seconds=0.05
                    )

        # The defect this change fixes: the requested project's own Editor is
        # actually launched instead of stalling on a recovery wait.
        launch_unity.assert_called_once()
        # The unrelated project's endpoint must never be persisted as this
        # project's session artifact.
        persist_ready.assert_not_called()


if __name__ == "__main__":
    unittest.main()
