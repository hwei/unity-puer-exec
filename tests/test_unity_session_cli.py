import json
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

import unity_puer_exec  # type: ignore
import unity_session  # type: ignore


SAMPLE_PROJECT_PATH = "X:/unity-project"


def _make_session():
    session = unity_session.UnitySession(
        owner="launched",
        base_url="http://127.0.0.1:55231",
        project_path=SAMPLE_PROJECT_PATH,
        unity_pid=1234,
        launched=True,
    )
    session.diagnostics = {"phase": "test"}
    return session


class UnityPuerExecCliTests(unittest.TestCase):
    def test_parser_exposes_formal_command_tree(self):
        parser = unity_puer_exec._build_parser()
        args = parser.parse_args(["wait-until-ready"])
        self.assertEqual(args.command, "wait-until-ready")

    def test_wait_until_ready_prefers_explicit_project_path(self):
        with mock.patch.dict(os.environ, {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-env"}, clear=False), mock.patch.object(
            unity_session,
            "ensure_session_ready",
            return_value=_make_session(),
        ) as ensure_session_ready:
            unity_puer_exec.run_cli(["wait-until-ready", "--project-path", "X:/from-arg"])

        self.assertEqual(ensure_session_ready.call_args.kwargs["project_path"], "X:/from-arg")

    def test_wait_until_ready_returns_success_payload(self):
        session = _make_session()

        with mock.patch.object(unity_session, "ensure_session_ready", return_value=session):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "wait-until-ready")
        self.assertEqual(payload["result"]["status"], "recovered")
        self.assertEqual(payload["session"]["unity_pid"], 1234)

    def test_wait_for_log_pattern_returns_success_payload(self):
        session = _make_session()
        session.diagnostics["matched_log_text"] = "[Build] complete"

        with mock.patch.object(unity_session, "create_observation_session", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-log-pattern", "--pattern", r"\[Build\] complete", "--timeout-seconds", "5"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "wait-for-log-pattern")
        self.assertEqual(payload["result"]["status"], "log_pattern_matched")
        self.assertEqual(payload["result"]["diagnostics"]["matched_log_text"], "[Build] complete")

    def test_exec_reads_file_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("return 7;", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.cli,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed"}), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["code"], "return 7;")
        self.assertEqual(json.loads(stdout)["status"], "completed")

    def test_get_log_source_returns_success_payload(self):
        session = _make_session()
        result = {"status": "log_source_available", "source": "file", "path": "X:/Editor.log"}

        with mock.patch.object(unity_session, "get_log_source", return_value=(session, result)):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-log-source"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["operation"], "get-log-source")
        self.assertEqual(payload["result"]["status"], "log_source_available")
        self.assertEqual(payload["result"]["path"], "X:/Editor.log")

    def test_get_log_source_no_target_maps_to_exit_code_15(self):
        with mock.patch.object(unity_session, "get_log_source", return_value=None):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-log-source"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_NO_OBSERVATION_TARGET)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "no_observation_target")

    def test_ensure_stopped_not_stopped_maps_to_exit_code_16(self):
        with mock.patch.object(unity_session, "ensure_stopped", return_value=(False, _make_session())):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["ensure-stopped", "--inspect-only"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_NOT_STOPPED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "not_stopped")

    def test_address_conflict_is_usage_error(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["wait-until-ready", "--project-path", "X:/a", "--base-url", "http://127.0.0.1:55231"]
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "address_conflict")

    def test_launch_error_maps_to_exit_code_20(self):
        session = _make_session()
        error = unity_session.UnityLaunchError("failed to launch", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_START_FAILED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_start_failed")
        self.assertEqual(payload["session"]["unity_pid"], 1234)

    def test_not_ready_error_maps_to_exit_code_21(self):
        session = _make_session()
        error = unity_session.UnityNotReadyError("not ready", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_NOT_READY)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_not_ready")


if __name__ == "__main__":
    unittest.main()
