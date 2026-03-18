import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_session_common  # type: ignore
import unity_session_env  # type: ignore
import unity_session_logs  # type: ignore
import unity_session_process  # type: ignore
import unity_session_wait  # type: ignore


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


if __name__ == "__main__":
    unittest.main()
