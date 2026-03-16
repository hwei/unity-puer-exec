import json
import os
import sys
import tempfile
import unittest
from base64 import urlsafe_b64decode
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

    def test_top_level_help_renders_formal_sections(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Overview", stdout)
        self.assertIn("Commands", stdout)
        self.assertIn("Global Selector Rules", stdout)
        self.assertIn("Common Workflows", stdout)
        self.assertIn("cold-start-exec-and-get-result", stdout)
        self.assertIn("See `exec --help`.", stdout)

    def test_empty_invocation_matches_top_level_help_contract(self):
        empty_exit_code, empty_stdout, empty_stderr = unity_puer_exec.run_cli([])
        help_exit_code, help_stdout, help_stderr = unity_puer_exec.run_cli(["--help"])

        self.assertEqual(empty_exit_code, 0)
        self.assertEqual(empty_stderr, "")
        self.assertEqual(help_exit_code, 0)
        self.assertEqual(help_stderr, "")
        self.assertEqual(empty_stdout, help_stdout)

    def test_exec_help_renders_quick_start_more_help_and_workflows(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Quick Start", stdout)
        self.assertIn("More Help", stdout)
        self.assertIn("Related Workflows", stdout)
        self.assertIn("`--help-args`", stdout)
        self.assertIn("`--help-status`", stdout)
        self.assertIn("cold-start-exec-and-get-result", stdout)

    def test_exec_help_args_renders_argument_template(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Arguments", stdout)
        self.assertIn("Selector Rules", stdout)
        self.assertIn("Timeout Rules", stdout)
        self.assertIn("`--file <path>`", stdout)
        self.assertIn("`--code <inline-js>`", stdout)

    def test_get_result_help_status_renders_exit_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-result", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Success Statuses", stdout)
        self.assertIn("Non-success Statuses", stdout)
        self.assertIn("`session_stale` -> exit 14", stdout)
        self.assertIn("`missing` -> exit 13", stdout)

    def test_help_example_renders_known_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "long-job-and-log-pattern"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Goal", stdout)
        self.assertIn("Steps", stdout)
        self.assertIn("What To Notice", stdout)
        self.assertIn("fake workload", stdout)
        self.assertIn("reduces the chance of missing an early log line", stdout)

    def test_exit_help_example_renders_inline_request_exit_script(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "request-editor-exit-via-exec"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Example script body:", stdout)
        self.assertIn("const EditorApplication = puer.loadType('UnityEditor.EditorApplication');", stdout)
        self.assertIn("EditorApplication.Exit(0);", stdout)
        self.assertIn("Expected observation:", stdout)

    def test_help_example_unknown_id_is_usage_error_on_stderr(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "missing-example"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("unknown example id: missing-example", stderr)
        self.assertIn("available examples:", stderr)
        self.assertIn("cold-start-exec-and-get-result", stderr)

    def test_deep_help_rejects_extra_execution_arguments(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args", "--project-path", "X:/project"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("usage: unity-puer-exec exec [--help | --help-args | --help-status]", stderr)

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
                unity_session,
                "inspect_direct_service",
                return_value=(True, {"ok": True, "status": "ready", "session_marker": "marker-1"}, None),
            ), mock.patch.object(
                unity_puer_exec.cli,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps({"ok": True, "status": "running", "job_id": "job-7"}), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path)])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["code"], "return 7;")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertIn("continuation_token", body)
        token_payload = json.loads(urlsafe_b64decode(body["continuation_token"] + "=" * (-len(body["continuation_token"]) % 4)))
        self.assertEqual(token_payload["job_id"], "job-7")
        self.assertEqual(token_payload["session_marker"], "marker-1")

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
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "address_conflict")

    def test_get_result_uses_continuation_token_routing(self):
        token = unity_puer_exec._encode_continuation_token(
            {
                "v": unity_puer_exec.CONTINUATION_TOKEN_VERSION,
                "base_url": "http://127.0.0.1:55231",
                "job_id": "job-22",
                "session_marker": "marker-22",
            }
        )

        with mock.patch.object(
            unity_session,
            "inspect_direct_service",
            return_value=(True, {"ok": True, "status": "ready", "session_marker": "marker-22"}, None),
        ), mock.patch.object(
            unity_puer_exec.cli,
            "invoke_command",
            return_value=(0, json.dumps({"ok": True, "status": "completed", "job_id": "job-22", "result": {"value": 9}}), ""),
        ) as invoke_command:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["get-result", "--continuation-token", token, "--wait-timeout-ms", "800"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            invoke_command.call_args.args,
            ("get-result", "http://127.0.0.1:55231", {"job_id": "job-22", "wait_timeout_ms": 800}, 800),
        )
        self.assertEqual(json.loads(stdout)["status"], "completed")

    def test_get_result_reports_session_stale_on_marker_mismatch(self):
        token = unity_puer_exec._encode_continuation_token(
            {
                "v": unity_puer_exec.CONTINUATION_TOKEN_VERSION,
                "base_url": "http://127.0.0.1:55231",
                "job_id": "job-23",
                "session_marker": "marker-old",
            }
        )

        with mock.patch.object(
            unity_session,
            "inspect_direct_service",
            return_value=(True, {"ok": True, "status": "ready", "session_marker": "marker-new"}, None),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-result", "--continuation-token", token])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_SESSION_STATE)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "session_stale")
        self.assertEqual(payload["job_id"], "job-23")

    def test_get_result_rejects_malformed_continuation_token(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-result", "--continuation-token", "%%%"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "failed")

    def test_wait_for_log_pattern_rejects_invalid_regex(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-log-pattern", "--pattern", "("])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "failed")

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
