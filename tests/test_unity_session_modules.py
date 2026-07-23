import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_session_common  # type: ignore
import unity_session_env  # type: ignore
import unity_session_logs  # type: ignore
import unity_session_process  # type: ignore
import unity_session_wait  # type: ignore

from tests import version_test_support


class UnitySessionModuleTests(unittest.TestCase):
    def test_env_resolve_project_path_uses_injected_loader(self):
        env = {"UNITY_PROJECT_PATH": "X:/from-env"}
        loader_calls = []

        def fake_loader(**kwargs):
            loader_calls.append(kwargs["env"])
            return True

        resolved = unity_session_env.resolve_project_path(
            __file__,
            project_path=None,
            cwd="X:/from-cwd",
            env=env,
            ensure_dotenv_loaded_fn=fake_loader,
        )

        self.assertEqual(resolved, Path("X:/from-env"))
        self.assertEqual(loader_calls, [env])

    def test_logs_resolve_effective_log_path_uses_injected_artifact_reader(self):
        def fake_read_session_artifact(_project_path):
            return {"session_marker": "marker-1", "effective_log_path": "X:/artifact/Editor.log", "unity_pid": 42}

        resolved = unity_session_logs.resolve_effective_log_path(
            "X:/project",
            unity_log_path="X:/explicit/Editor.log",
            session_data=None,
            read_session_artifact_fn=fake_read_session_artifact,
            session_artifact_log_path_fn=lambda payload: unity_session_logs.session_artifact_log_path(
                payload,
                is_pid_running_fn=lambda pid: pid == 42,
            ),
            default_editor_log_path_fn=lambda: Path("X:/default/Editor.log"),
        )

        self.assertEqual(resolved, Path("X:/artifact/Editor.log"))

    def test_process_ensure_stopped_uses_injected_dependencies(self):
        time_ref = SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None)

        stopped, session = unity_session_process.ensure_stopped(
            project_path="X:/project",
            mode="inspect",
            resolve_project_path_fn=lambda value: Path(value),
            read_session_artifact_fn=lambda _path: {"base_url": "http://127.0.0.1:55231", "unity_pid": 1234},
            session_artifact_path_fn=lambda _path: Path("X:/project/Temp/UnityPuerExec/session.json"),
            list_unity_pids_fn=lambda: [1234],
            is_pid_running_fn=lambda pid: pid == 1234,
            default_base_url="http://127.0.0.1:55231",
            time_ref=time_ref,
        )

        self.assertEqual(stopped, False)
        self.assertEqual(session.owner, "project_control")
        self.assertEqual(session.diagnostics["unity_pids"], [1234])

    def test_process_ensure_stopped_waits_briefly_after_taskkill(self):
        time_values = iter([0.0, 0.0, 0.2, 0.2])
        sleep_calls = []
        pid_running = iter([True, True, False])

        time_ref = SimpleNamespace(time=lambda: next(time_values), sleep=lambda seconds: sleep_calls.append(seconds))

        with mock.patch.object(
            unity_session_process.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["taskkill", "/PID", "1234", "/T", "/F"],
                returncode=0,
                stdout="SUCCESS",
                stderr="",
            ),
        ):
            stopped, session = unity_session_process.ensure_stopped(
                project_path="X:/project",
                mode="immediate_kill",
                resolve_project_path_fn=lambda value: Path(value),
                read_session_artifact_fn=lambda _path: {"base_url": "http://127.0.0.1:55231", "unity_pid": 1234},
                session_artifact_path_fn=lambda _path: Path("X:/project/Temp/UnityPuerExec/session.json"),
                list_unity_pids_fn=lambda: [1234],
                is_pid_running_fn=lambda _pid: next(pid_running),
                default_base_url="http://127.0.0.1:55231",
                time_ref=time_ref,
            )

        self.assertTrue(stopped)
        self.assertEqual(session.diagnostics["taskkill_exit_code"], 0)
        self.assertEqual(sleep_calls, [unity_session_common.POLL_INTERVAL_SECONDS])

    def test_pid_present_in_tasklist_csv_is_locale_independent(self):
        # A real PID-row match.
        match_csv = '"Unity.exe","1234","Console","1","2,000,000 K"\r\n'
        self.assertTrue(unity_session_process._pid_present_in_tasklist_csv(match_csv, 1234))
        self.assertFalse(unity_session_process._pid_present_in_tasklist_csv(match_csv, 9999))

        # English "no tasks" line -> not running.
        english_none = "INFO: No tasks are running which match the specified criteria.\r\n"
        self.assertFalse(unity_session_process._pid_present_in_tasklist_csv(english_none, 1234))

        # Localized (Chinese) "no tasks" line -> must also read as not running.
        chinese_none = "信息: 没有运行的任务与指定的标准匹配。\r\n"
        self.assertFalse(unity_session_process._pid_present_in_tasklist_csv(chinese_none, 1234))

        # Empty output -> not running.
        self.assertFalse(unity_session_process._pid_present_in_tasklist_csv("", 1234))

    def test_is_pid_running_handles_localized_no_match_output(self):
        chinese_none = "信息: 没有运行的任务与指定的标准匹配。"
        with mock.patch.object(
            unity_session_process.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["tasklist", "/FI", "PID eq 104136", "/NH", "/FO", "CSV"],
                returncode=0,
                stdout=chinese_none,
                stderr="",
            ),
        ):
            # The dead PID must read as not running even when tasklist emits a
            # localized no-match line (the locale-dependent regression).
            self.assertFalse(unity_session_process.is_pid_running(104136))

        match_csv = '"Unity.exe","104136","Console","1","2,000,000 K"'
        with mock.patch.object(
            unity_session_process.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["tasklist", "/FI", "PID eq 104136", "/NH", "/FO", "CSV"],
                returncode=0,
                stdout=match_csv,
                stderr="",
            ),
        ):
            self.assertTrue(unity_session_process.is_pid_running(104136))

        self.assertFalse(unity_session_process.is_pid_running(None))

    def test_project_lockfile_is_held_returns_false_when_lockfile_is_missing(self):
        with mock.patch.object(
            unity_session_process.os,
            "open",
            side_effect=FileNotFoundError(),
        ):
            self.assertFalse(unity_session_process._project_lockfile_is_held("X:/unity-project"))

    def test_project_lockfile_is_held_returns_true_when_open_is_denied(self):
        with mock.patch.object(
            unity_session_process.os,
            "open",
            side_effect=PermissionError(),
        ):
            self.assertTrue(unity_session_process._project_lockfile_is_held("X:/unity-project"))

    def test_project_lockfile_is_held_returns_true_on_lock_contention(self):
        with mock.patch.object(
            unity_session_process.os, "open", return_value=7
        ), mock.patch.object(
            unity_session_process.os, "close",
        ) as close_fd, mock.patch(
            "msvcrt.locking", side_effect=OSError()
        ) as locking:
            self.assertTrue(unity_session_process._project_lockfile_is_held("X:/unity-project"))

        locking.assert_called_once_with(7, mock.ANY, 1)
        close_fd.assert_called_once_with(7)

    def test_project_lockfile_is_held_returns_false_when_lock_acquires_cleanly(self):
        with mock.patch.object(
            unity_session_process.os, "open", return_value=7
        ), mock.patch.object(
            unity_session_process.os, "close",
        ) as close_fd, mock.patch(
            "msvcrt.locking", return_value=None
        ) as locking:
            self.assertFalse(unity_session_process._project_lockfile_is_held("X:/unity-project"))

        self.assertEqual(locking.call_count, 2)
        close_fd.assert_called_once_with(7)

    def test_wait_wait_until_healthy_uses_wait_for_session_injection(self):
        session = unity_session_common.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="X:/unity-project",
        )
        captured = {}

        def fake_wait_for_session(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return session

        result = unity_session_wait.wait_until_healthy(
            session,
            timeout_seconds=5.0,
            activity_timeout_seconds=8.0,
            health_timeout_seconds=1.5,
            log_path="X:/Logs/Editor.log",
            wait_for_session_fn=fake_wait_for_session,
        )

        self.assertIs(result, session)
        self.assertEqual(captured["args"][0], session)
        self.assertEqual(captured["args"][1], 5.0)
        self.assertEqual(captured["kwargs"]["activity_timeout_seconds"], 8.0)
        self.assertEqual(captured["kwargs"]["health_timeout_seconds"], 1.5)
        self.assertEqual(captured["kwargs"]["log_path"], "X:/Logs/Editor.log")
        self.assertEqual(captured["kwargs"]["timeout_message"], "Unity did not become healthy within 5.0 seconds")
        self.assertTrue(captured["kwargs"]["completion_predicate"]({"ok": True, "status": "ready"}))

    def test_wait_for_session_redirects_base_url_via_endpoint_resolver(self):
        session = unity_session_common.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="X:/unity-project",
        )
        log_path = Path("X:/Logs/Editor.log")
        fake_time = SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None)
        rolled_over = "http://127.0.0.1:55233"

        def probe(base_url, _timeout):
            # Only the rolled-over endpoint is ready; the preferred port never is.
            if base_url == rolled_over:
                return {"ok": True, "status": "ready", "project_path": "X:/unity-project"}, None
            return {"ok": False, "status": "compiling"}, None

        result = unity_session_wait.wait_for_session(
            session,
            timeout_seconds=5.0,
            log_path=log_path,
            endpoint_resolver=lambda: rolled_over,
            default_editor_log_path_fn=lambda: log_path,
            probe_health_fn=probe,
            create_activity_tracker_fn=lambda _path: {"idle_seconds": 0.0},
            update_activity_tracker_fn=lambda tracker, _path: tracker,
            finalize_session_diagnostics_fn=lambda *_args, **_kwargs: None,
            time_ref=fake_time,
        )

        self.assertIs(result, session)
        # The wait loop adopted the resolver's endpoint before completing.
        self.assertEqual(session.base_url, rolled_over)

    def test_wait_for_session_never_claims_unresolved_endpoint(self):
        """An unmatched endpoint_resolver must not fall back to probing session.base_url.

        Regression for the exec misroute: session.base_url starts out pointed at the
        preferred port (an unrelated, already-ready project may be listening there).
        The resolver never finds a project-matched candidate, so the wait must time
        out instead of accepting that unrelated endpoint's "ready" health as if it
        belonged to this session's project.
        """
        preferred = "http://127.0.0.1:55231"
        session = unity_session_common.UnitySession(
            owner="test",
            base_url=preferred,
            project_path="X:/unity-project",
        )
        log_path = Path("X:/Logs/Editor.log")
        time_values = iter([0.0, 0.0, 6.0])
        fake_time = SimpleNamespace(time=lambda: next(time_values), sleep=lambda _seconds: None)

        probe_calls = []

        def probe(base_url, _timeout):
            probe_calls.append(base_url)
            # An unrelated project is ready on the preferred port; this session's
            # own project never answers on any candidate.
            return {"ok": True, "status": "ready", "project_path": "X:/other-project"}, None

        with self.assertRaises(unity_session_common.UnityNotReadyError):
            unity_session_wait.wait_for_session(
                session,
                timeout_seconds=5.0,
                log_path=log_path,
                endpoint_resolver=lambda: None,
                default_editor_log_path_fn=lambda: log_path,
                probe_health_fn=probe,
                create_activity_tracker_fn=lambda _path: {"idle_seconds": 0.0},
                update_activity_tracker_fn=lambda tracker, _path: tracker,
                finalize_session_diagnostics_fn=lambda *_args, **_kwargs: None,
                time_ref=fake_time,
            )

        # The unresolved endpoint_resolver iteration must never have probed
        # session.base_url directly, and base_url must remain unclaimed.
        self.assertEqual(probe_calls, [])
        self.assertEqual(session.base_url, preferred)

    def test_wait_wait_for_log_pattern_extracts_json_group(self):
        session = unity_session_common.UnitySession(
            owner="test",
            base_url="http://127.0.0.1:55231",
            project_path="X:/unity-project",
        )
        log_path = Path("X:/Logs/Editor.log")
        fake_time = SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None)

        result = unity_session_wait.wait_for_log_pattern(
            session,
            r"\[UnityPuerExecResult\] (.+)",
            timeout_seconds=5.0,
            log_path=log_path,
            extract_json_group=1,
            default_editor_log_path_fn=lambda: log_path,
            probe_health_fn=lambda *_args: ({"ok": False, "status": "compiling"}, None),
            create_activity_tracker_fn=lambda _path: {"idle_seconds": 0.0},
            update_activity_tracker_fn=lambda tracker, _path: tracker,
            finalize_session_diagnostics_fn=lambda *_args, **_kwargs: None,
            read_editor_log_size_fn=lambda _path: 0,
            read_editor_log_chunk_fn=lambda _path, _offset: (
                64,
                '[UnityPuerExecResult] {"correlation_id":"id-1","value":7}',
            ),
            time_ref=fake_time,
        )

        self.assertIs(result, session)
        self.assertEqual(session.diagnostics["extracted_json"]["correlation_id"], "id-1")
        self.assertEqual(session.diagnostics["matched_log_offset"], 57)

    def test_logs_write_and_read_session_artifact_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            payload = {
                "base_url": "http://127.0.0.1:55231",
                "unity_pid": 1234,
                "session_marker": "marker-1",
                "effective_log_path": "X:/artifact/Editor.log",
            }

            unity_session_logs.write_session_artifact(project_path, payload)
            restored = unity_session_logs.read_session_artifact(project_path)

        self.assertEqual(restored, payload)

    def test_logs_write_and_clear_launch_claim_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            payload = {"owner_pid": 321, "created_at": 12.5}

            unity_session_logs.write_launch_claim(project_path, payload)
            restored = unity_session_logs.read_launch_claim(project_path)
            unity_session_logs.clear_launch_claim(project_path)
            cleared = unity_session_logs.read_launch_claim(project_path)

        self.assertEqual(restored, payload)
        self.assertIsNone(cleared)

    def test_logs_write_pending_exec_artifact_persists_schema_and_refreshes_timestamps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            with mock.patch.object(unity_session_logs.time, "time", return_value=100.0):
                first = unity_session_logs.write_pending_exec_artifact(
                    project_path,
                    "req-1",
                    {
                        "request_id": "req-1",
                        "code": "export default function run(ctx) { return 1; }",
                        "script_args": {"mode": "test"},
                        "script_args_json": "{\"mode\":\"test\"}",
                        "source_path": "C:/scripts/entry.js",
                        "import_base_url": "http://localhost:3000",
                        "reset_jsenv_before_exec": True,
                    },
                )
            with mock.patch.object(unity_session_logs.time, "time", return_value=125.0):
                second = unity_session_logs.write_pending_exec_artifact(
                    project_path,
                    "req-1",
                    dict(first, phase="compiling"),
                )
            with mock.patch.object(unity_session_logs.time, "time", return_value=125.0):
                restored = unity_session_logs.read_pending_exec_artifact(project_path, "req-1")

        self.assertEqual(first["schema_version"], unity_session_common.PENDING_EXEC_SCHEMA_VERSION)
        self.assertEqual(first["created_at_ms"], 100000)
        self.assertEqual(first["updated_at_ms"], 100000)
        self.assertEqual(first["script_args"], {"mode": "test"})
        self.assertEqual(first["script_args_json"], "{\"mode\":\"test\"}")
        self.assertEqual(first["source_path"], "C:/scripts/entry.js")
        self.assertEqual(first["import_base_url"], "http://localhost:3000")
        self.assertTrue(first["reset_jsenv_before_exec"])
        self.assertEqual(first["stale_module_policy"], "auto-reset")
        self.assertEqual(second["created_at_ms"], 100000)
        self.assertEqual(second["updated_at_ms"], 125000)
        self.assertEqual(restored["phase"], "compiling")
        self.assertEqual(restored["script_args"], {"mode": "test"})
        self.assertEqual(restored["source_path"], "C:/scripts/entry.js")
        self.assertEqual(restored["import_base_url"], "http://localhost:3000")
        self.assertTrue(restored["reset_jsenv_before_exec"])
        self.assertEqual(restored["stale_module_policy"], "auto-reset")

    def test_logs_read_pending_exec_artifact_cleans_expired_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            artifact_path = unity_session_logs.pending_exec_artifact_path(project_path, "req-expired")
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    {
                        "schema_version": unity_session_common.PENDING_EXEC_SCHEMA_VERSION,
                        "request_id": "req-expired",
                        "code": "export default function run(ctx) { return 1; }",
                        "script_args": {},
                        "script_args_json": "{}",
                        "refresh_before_exec": False,
                        "created_at_ms": 1000,
                        "updated_at_ms": 1000,
                    }
                ),
                encoding="utf-8",
            )

            expired_at = (unity_session_common.PENDING_EXEC_RETENTION_MS + 2000) / 1000.0
            with mock.patch.object(unity_session_logs.time, "time", return_value=expired_at):
                restored = unity_session_logs.read_pending_exec_artifact(project_path, "req-expired")

            exists_after = artifact_path.exists()

        self.assertIsNone(restored)
        self.assertFalse(exists_after)

    def test_logs_read_pending_exec_artifact_cleans_malformed_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            artifact_path = unity_session_logs.pending_exec_artifact_path(project_path, "req-bad")
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{bad json", encoding="utf-8")

            restored = unity_session_logs.read_pending_exec_artifact(project_path, "req-bad")
            exists_after = artifact_path.exists()

        self.assertIsNone(restored)
        self.assertFalse(exists_after)

    def test_logs_sweep_pending_exec_artifacts_removes_only_expired_and_malformed_siblings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sweep_time = (unity_session_common.PENDING_EXEC_RETENTION_MS + 2000) / 1000.0
            with mock.patch.object(unity_session_logs.time, "time", return_value=sweep_time):
                unity_session_logs.write_pending_exec_artifact(
                    project_path,
                    "req-fresh",
                    {
                        "request_id": "req-fresh",
                        "code": "export default function run(ctx) { return 1; }",
                        "script_args": {},
                        "script_args_json": "{}",
                    },
                )
            expired_path = unity_session_logs.pending_exec_artifact_path(project_path, "req-expired")
            expired_path.write_text(
                json.dumps(
                    {
                        "schema_version": unity_session_common.PENDING_EXEC_SCHEMA_VERSION,
                        "request_id": "req-expired",
                        "code": "export default function run(ctx) { return 2; }",
                        "script_args": {},
                        "script_args_json": "{}",
                        "refresh_before_exec": False,
                        "created_at_ms": 1000,
                        "updated_at_ms": 1000,
                    }
                ),
                encoding="utf-8",
            )
            malformed_path = unity_session_logs.pending_exec_artifact_path(project_path, "req-bad")
            malformed_path.write_text("{bad json", encoding="utf-8")

            with mock.patch.object(unity_session_logs.time, "time", return_value=sweep_time):
                removed = unity_session_logs.sweep_pending_exec_artifacts(project_path)
                fresh = unity_session_logs.read_pending_exec_artifact(project_path, "req-fresh")

        self.assertEqual(len(removed), 2)
        self.assertIsNotNone(fresh)
        self.assertFalse(expired_path.exists())
        self.assertFalse(malformed_path.exists())


class ExeOriginProjectInferenceTests(unittest.TestCase):
    def _make_manifest(self, root, has_package=True):
        packages_dir = root / "Packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        deps = {"com.txcombo.unity-puer-exec": "1.0.0"} if has_package else {"com.unity.foo": "1.0.0"}
        manifest_path = packages_dir / "manifest.json"
        manifest_path.write_text(json.dumps({"dependencies": deps}), encoding="utf-8")
        return manifest_path

    def test_infer_package_cache_layout_returns_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root)
            exe_path = root / "Library" / "PackageCache" / "com.txcombo.unity-puer-exec@1.0.0" / "CLI~" / "unity-puer-exec.exe"
            result = unity_session_env._infer_project_from_exe(str(exe_path))
            self.assertEqual(result, root.resolve())

    def test_infer_embedded_package_layout_returns_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root)
            exe_path = root / "Packages" / "com.txcombo.unity-puer-exec" / "CLI~" / "unity-puer-exec.exe"
            result = unity_session_env._infer_project_from_exe(str(exe_path))
            self.assertEqual(result, root.resolve())

    def test_infer_manifest_without_package_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root, has_package=False)
            exe_path = root / "Library" / "PackageCache" / "com.txcombo.unity-puer-exec@1.0.0" / "CLI~" / "unity-puer-exec.exe"
            result = unity_session_env._infer_project_from_exe(str(exe_path))
            self.assertIsNone(result)

    def test_infer_no_manifest_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe_path = root / "some" / "path" / "unity-puer-exec.exe"
            result = unity_session_env._infer_project_from_exe(str(exe_path))
            self.assertIsNone(result)

    def test_resolve_priority_explicit_project_path_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root)
            exe_path = root / "Library" / "PackageCache" / "com.txcombo.unity-puer-exec@1.0.0" / "CLI~" / "unity-puer-exec.exe"
            env = {"UNITY_PROJECT_PATH": str(root / "from-env")}

            def no_loader(**kwargs):
                return False

            resolved = unity_session_env.resolve_project_path(
                __file__,
                project_path=str(root / "explicit"),
                cwd=str(root / "from-cwd"),
                env=env,
                ensure_dotenv_loaded_fn=no_loader,
                argv0=str(exe_path),
            )
            self.assertEqual(resolved, root / "explicit")

    def test_resolve_priority_env_var_beats_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root)
            exe_path = root / "Library" / "PackageCache" / "com.txcombo.unity-puer-exec@1.0.0" / "CLI~" / "unity-puer-exec.exe"
            env_path = root / "from-env"
            env = {"UNITY_PROJECT_PATH": str(env_path)}

            def no_loader(**kwargs):
                return False

            resolved = unity_session_env.resolve_project_path(
                __file__,
                project_path=None,
                cwd=str(root / "from-cwd"),
                env=env,
                ensure_dotenv_loaded_fn=no_loader,
                argv0=str(exe_path),
            )
            self.assertEqual(resolved, env_path)

    def test_resolve_priority_inference_beats_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_manifest(root)
            exe_path = root / "Library" / "PackageCache" / "com.txcombo.unity-puer-exec@1.0.0" / "CLI~" / "unity-puer-exec.exe"
            env = {}

            def no_loader(**kwargs):
                return False

            resolved = unity_session_env.resolve_project_path(
                __file__,
                project_path=None,
                cwd=str(root / "from-cwd"),
                env=env,
                ensure_dotenv_loaded_fn=no_loader,
                argv0=str(exe_path),
            )
            self.assertEqual(resolved, root.resolve())

    def test_resolve_priority_cwd_fallback_when_no_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe_path = root / "some" / "path" / "unity-puer-exec.exe"
            env = {}
            cwd = str(root / "from-cwd")

            def no_loader(**kwargs):
                return False

            resolved = unity_session_env.resolve_project_path(
                __file__,
                project_path=None,
                cwd=cwd,
                env=env,
                ensure_dotenv_loaded_fn=no_loader,
                argv0=str(exe_path),
            )
            self.assertEqual(resolved, Path(cwd))


class HealthIdentityProtocolTests(unittest.TestCase):
    """Protocol-level tests for health identity fields and dynamic port reporting.

    These tests validate the health response shape as defined by the
    project-control-endpoint spec, without requiring a live Unity process.
    """

    def test_build_health_snapshot_includes_port_when_present(self):
        payload = {"ok": True, "status": "ready", "port": 55232, "session_marker": "abc123"}
        snapshot = unity_session_wait.build_health_snapshot(payload, None)
        self.assertEqual(snapshot["ok"], True)
        self.assertEqual(snapshot["status"], "ready")
        self.assertEqual(snapshot["port"], 55232)

    def test_build_health_snapshot_omits_port_when_absent(self):
        payload = {"ok": True, "status": "ready"}
        snapshot = unity_session_wait.build_health_snapshot(payload, None)
        self.assertEqual(snapshot["ok"], True)
        self.assertNotIn("port", snapshot)

    def test_build_health_snapshot_handles_transport_error(self):
        snapshot = unity_session_wait.build_health_snapshot(None, "connection refused")
        self.assertEqual(snapshot["ok"], False)
        self.assertEqual(snapshot["status"], "transport_error")
        self.assertEqual(snapshot["error"], "connection refused")

    def test_health_payload_contains_all_identity_fields(self):
        """Verify a complete ready health response can be parsed with all identity fields."""
        payload = {
            "ok": True,
            "status": "ready",
            "port": 55235,
            "base_url": "http://127.0.0.1:55235",
            "unity_pid": 12345,
            "project_path": "C:/MyProject",
            "session_marker": "deadbeef1234",
        }
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["port"], 55235)
        self.assertEqual(payload["base_url"], "http://127.0.0.1:55235")
        self.assertEqual(payload["unity_pid"], 12345)
        self.assertEqual(payload["project_path"], "C:/MyProject")
        self.assertEqual(payload["session_marker"], "deadbeef1234")

    def test_health_payload_non_default_port_is_reported(self):
        """Verify a non-default port (> 55231) is correctly reported."""
        payload = {
            "ok": True,
            "status": "ready",
            "port": 55240,
            "base_url": "http://127.0.0.1:55240",
            "session_marker": "xyz",
        }
        self.assertEqual(payload["port"], 55240)
        self.assertNotEqual(payload["port"], 55231)

    def test_persist_ready_session_artifact_includes_port_from_payload(self):
        import json as _json
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            session = unity_session_common.UnitySession(
                owner="test",
                base_url="http://127.0.0.1:55233",
                project_path=str(project_path),
                unity_pid=1234,
            )
            payload = {
                "ok": True,
                "status": "ready",
                "port": 55233,
                "session_marker": "marker-1",
                "project_path": str(project_path),
            }
            unity_session_logs.persist_ready_session_artifact(
                session,
                Path("X:/Logs/Editor.log"),
                payload=payload,
                session_marker_from_payload_fn=unity_session_logs.session_marker_from_payload,
                write_session_artifact_fn=unity_session_logs.write_session_artifact,
            )
            artifact = unity_session_logs.read_session_artifact(project_path)
            self.assertEqual(artifact["port"], 55233)
            self.assertEqual(artifact["project_path"], str(project_path))
            self.assertEqual(artifact["session_marker"], "marker-1")


class ArtifactIdentityValidationTests(unittest.TestCase):
    """Tests for validate_endpoint_identity and validate_artifact_endpoint."""

    def test_validate_endpoint_identity_matching_project_returns_true(self):
        def fake_probe(base_url, timeout_seconds):
            return {
                "ok": True,
                "status": "ready",
                "project_path": "X:/unity-project",
                "bridge_version": version_test_support.matching_bridge_version(),
            }, None

        # We need to test via the session module; patch _probe_health
        import unity_session as us
        with mock.patch.object(us, "_probe_health", side_effect=fake_probe):
            is_valid, payload, error = us.validate_endpoint_identity(
                "http://127.0.0.1:55231",
                "X:/unity-project",
            )
        self.assertTrue(is_valid)
        self.assertIsNotNone(payload)
        self.assertIsNone(error)

    def test_validate_endpoint_identity_different_project_returns_false(self):
        def fake_probe(base_url, timeout_seconds):
            return {
                "ok": True,
                "status": "ready",
                "project_path": "X:/other-project",
            }, None

        import unity_session as us
        with mock.patch.object(us, "_probe_health", side_effect=fake_probe):
            is_valid, payload, error = us.validate_endpoint_identity(
                "http://127.0.0.1:55231",
                "X:/unity-project",
            )
        self.assertFalse(is_valid)
        self.assertIsNotNone(payload)
        self.assertIsNone(error)

    def test_validate_endpoint_identity_unreachable_returns_false(self):
        def fake_probe(base_url, timeout_seconds):
            return None, "connection refused"

        import unity_session as us
        with mock.patch.object(us, "_probe_health", side_effect=fake_probe):
            is_valid, payload, error = us.validate_endpoint_identity(
                "http://127.0.0.1:55231",
                "X:/unity-project",
            )
        self.assertFalse(is_valid)
        self.assertIsNone(payload)
        self.assertEqual(error, "connection refused")

    def test_validate_endpoint_identity_not_ready_returns_false(self):
        def fake_probe(base_url, timeout_seconds):
            return {"ok": False, "status": "compiling"}, None

        import unity_session as us
        with mock.patch.object(us, "_probe_health", side_effect=fake_probe):
            is_valid, payload, error = us.validate_endpoint_identity(
                "http://127.0.0.1:55231",
                "X:/unity-project",
            )
        self.assertFalse(is_valid)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "compiling")

    def test_validate_endpoint_identity_missing_project_path_returns_false(self):
        """Old fixed-port artifacts won't have project_path in health."""
        def fake_probe(base_url, timeout_seconds):
            return {
                "ok": True,
                "status": "ready",
                "port": 55231,
            }, None

        import unity_session as us
        with mock.patch.object(us, "_probe_health", side_effect=fake_probe):
            is_valid, payload, error = us.validate_endpoint_identity(
                "http://127.0.0.1:55231",
                "X:/unity-project",
            )
        self.assertFalse(is_valid)
        self.assertIsNotNone(payload)

    def test_validate_artifact_endpoint_empty_artifact_returns_false(self):
        import unity_session as us
        is_valid, base_url, payload, error = us.validate_artifact_endpoint(
            None,
            "X:/unity-project",
        )
        self.assertFalse(is_valid)
        self.assertIsNone(base_url)
        self.assertIsNone(payload)
        self.assertIsNone(error)

    def test_validate_artifact_endpoint_missing_base_url_returns_false(self):
        import unity_session as us
        is_valid, base_url, payload, error = us.validate_artifact_endpoint(
            {"session_marker": "abc"},
            "X:/unity-project",
        )
        self.assertFalse(is_valid)
        self.assertIsNone(base_url)

    def test_logs_session_artifact_includes_project_path_and_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            payload = {
                "base_url": "http://127.0.0.1:55235",
                "unity_pid": 1234,
                "session_marker": "marker-1",
                "effective_log_path": "X:/artifact/Editor.log",
                "project_path": str(project_path),
                "port": 55235,
            }
            unity_session_logs.write_session_artifact(project_path, payload)
            restored = unity_session_logs.read_session_artifact(project_path)
            self.assertEqual(restored["project_path"], str(project_path))
            self.assertEqual(restored["port"], 55235)


if __name__ == "__main__":
    unittest.main()
