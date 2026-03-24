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
import unity_puer_exec_runtime  # type: ignore
import unity_session  # type: ignore


SAMPLE_PROJECT_PATH = "X:/unity-project"


def _make_session(project_path=SAMPLE_PROJECT_PATH):
    session = unity_session.UnitySession(
        owner="launched",
        base_url="http://127.0.0.1:55231",
        project_path=project_path,
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
        self.assertIn("Bridge Model", stdout)
        self.assertIn("Recommended Path", stdout)
        self.assertIn("Command Groups", stdout)
        self.assertIn("Primary Execution", stdout)
        self.assertIn("Supporting Observation", stdout)
        self.assertIn("Secondary / Troubleshooting", stdout)
        self.assertIn("Global Selector Rules", stdout)
        self.assertIn("Common Workflows", stdout)
        self.assertIn("get-blocker-state", stdout)
        self.assertIn("exec-and-wait-for-result-marker", stdout)
        self.assertIn("exec-and-wait-for-log-pattern", stdout)
        self.assertIn("load-and-call-csharp-type", stdout)
        self.assertIn("recover-exec-by-request-id", stdout)
        self.assertIn("See `exec --help`.", stdout)
        self.assertIn("start with `exec --project-path ...`", stdout)
        self.assertIn("not the normal first step", stdout)
        self.assertIn("PuerTS-style JavaScript-to-C# bridge", stdout)
        self.assertIn("do not assume bridged C# arrays or `List<T>` values behave exactly like native JS arrays", stdout)

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
        self.assertIn("exec-and-wait-for-result-marker", stdout)
        self.assertIn("load-and-call-csharp-type", stdout)
        self.assertIn("Normal first command for project-scoped work", stdout)
        self.assertIn("do not need `wait-until-ready` as the default first step", stdout)
        self.assertIn("PuerTS-style JavaScript-to-C# bridge", stdout)

    def test_exec_help_args_renders_argument_template(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Arguments", stdout)
        self.assertIn("Selector Rules", stdout)
        self.assertIn("Bridge Model", stdout)
        self.assertIn("Timeout Rules", stdout)
        self.assertIn("`--file <path>`", stdout)
        self.assertIn("`--code <inline-js>`", stdout)
        self.assertIn("`--request-id <id>`", stdout)
        self.assertIn("`--refresh-before-exec`", stdout)
        self.assertIn("`--include-diagnostics`", stdout)
        self.assertIn("`export default function", stdout)
        self.assertIn("Promise", stdout)
        self.assertIn("`puer.loadType(...)`", stdout)
        self.assertIn("Bridged C# arrays and `List<T>` values are not plain JS arrays", stdout)
        self.assertIn("https://puerts.github.io/docs/puerts/unity/tutorial/js2cs", stdout)

    def test_wait_for_exec_help_renders_recovery_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Preferred follow-up", stdout)
        self.assertIn("accepted exec `request_id`", stdout)

    def test_wait_for_log_pattern_help_mentions_log_workflow_example(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-log-pattern", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Quick Start", stdout)
        self.assertIn("exec-and-wait-for-log-pattern", stdout)
        self.assertIn("exec-and-wait-for-result-marker", stdout)

    def test_wait_for_exec_help_status_mentions_missing(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`missing` -> exit 13", stdout)
        self.assertIn("`modal_blocked` -> exit 19", stdout)
        self.assertIn("`phase`", stdout)

    def test_get_blocker_state_help_renders_query_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-blocker-state", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Secondary troubleshooting command", stdout)
        self.assertIn("supported Unity modal blocker", stdout)

    def test_get_blocker_state_help_status_mentions_modal_result(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-blocker-state", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`completed`: blocker inspection finished", stdout)

    def test_wait_for_result_marker_help_status_renders_exit_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-result-marker", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Success Statuses", stdout)
        self.assertIn("Non-success Statuses", stdout)
        self.assertIn("`session_stale` -> exit 14", stdout)
        self.assertIn("`no_observation_target` -> exit 15", stdout)

    def test_wait_until_ready_help_status_mentions_launch_conflict(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`launch_conflict` -> exit 20", stdout)

    def test_help_example_renders_known_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "exec-and-wait-for-result-marker"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Goal", stdout)
        self.assertIn("Steps", stdout)
        self.assertIn("What To Notice", stdout)
        self.assertIn("correlation_id", stdout)
        self.assertIn("log_offset", stdout)
        self.assertIn("Do not assume `running` already includes `result.correlation_id`", stdout)

    def test_log_pattern_help_example_renders_checkpointed_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "exec-and-wait-for-log-pattern"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Goal", stdout)
        self.assertIn("wait-for-log-pattern", stdout)
        self.assertIn("--include-log-offset", stdout)
        self.assertIn("--start-offset OFFSET", stdout)
        self.assertIn("direct host-log inspection", stdout)

    def test_recovery_help_example_renders_request_id_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "recover-exec-by-request-id"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("request_id", stdout)
        self.assertIn("wait-for-exec", stdout)
        self.assertIn("do not blindly retry with a fresh `request_id`", stdout)

    def test_bridge_help_example_renders_canonical_bridge_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "load-and-call-csharp-type"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Use the normal PuerTS-style bridge path", stdout)
        self.assertIn("const Math = puer.loadType('System.Math');", stdout)
        self.assertIn("const EditorApplication = puer.loadType('UnityEditor.EditorApplication');", stdout)
        self.assertIn("maxValue", stdout)
        self.assertIn("bridged C# arrays and `List<T>` values", stdout)
        self.assertIn("https://puerts.github.io/docs/puerts/unity/tutorial/js2cs", stdout)

    def test_exec_help_describes_running_without_immediate_correlation_id_guarantee(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`running`: the request is still active", stdout)
        self.assertIn("wait-for-exec --request-id", stdout)
        self.assertIn("`refreshing`", stdout)
        self.assertIn("`compiling`", stdout)
        self.assertIn("Promise return values are rejected", stdout)
        self.assertIn("`modal_blocked` -> exit 19", stdout)

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
        self.assertIn("exec-and-wait-for-result-marker", stderr)

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

    def test_wait_until_ready_forwards_unity_log_path(self):
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            return_value=_make_session(),
        ) as ensure_session_ready:
            unity_puer_exec.run_cli(["wait-until-ready", "--project-path", "X:/project", "--unity-log-path", "X:/Logs/Editor.log"])

        self.assertEqual(ensure_session_ready.call_args.kwargs["unity_log_path"], "X:/Logs/Editor.log")

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
        self.assertNotIn("diagnostics", payload)
        self.assertNotIn("diagnostics", payload["session"])

    def test_wait_until_ready_include_diagnostics_returns_top_level_diagnostics(self):
        session = _make_session()

        with mock.patch.object(unity_session, "ensure_session_ready", return_value=session):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready", "--include-diagnostics"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["diagnostics"]["phase"], "test")
        self.assertNotIn("diagnostics", payload["session"])

    def test_wait_for_log_pattern_returns_success_payload(self):
        session = _make_session()
        session.diagnostics["matched_log_text"] = "[Build] complete"
        session.diagnostics["matched_log_pattern"] = r"\[Build\] complete"

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
        self.assertNotIn("diagnostics", payload)
        self.assertNotIn("diagnostics", payload["result"])

    def test_wait_for_log_pattern_include_diagnostics_returns_top_level_diagnostics(self):
        session = _make_session()
        session.diagnostics["matched_log_text"] = "[Build] complete"
        session.diagnostics["matched_log_pattern"] = r"\[Build\] complete"

        with mock.patch.object(unity_session, "create_observation_session", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-log-pattern", "--pattern", r"\[Build\] complete", "--timeout-seconds", "5", "--include-diagnostics"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["diagnostics"]["matched_log_pattern"], r"\[Build\] complete")
        self.assertEqual(payload["diagnostics"]["matched_log_text"], "[Build] complete")

    def test_wait_for_log_pattern_extract_json_group_returns_parsed_object(self):
        session = _make_session()
        session.diagnostics["matched_log_pattern"] = r"\[UnityPuerExecResult\] (.+)"
        session.diagnostics["extracted_json"] = {"correlation_id": "id-1", "value": 7}

        with mock.patch.object(unity_session, "create_observation_session", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-log-pattern", "--pattern", r"\[UnityPuerExecResult\] (.+)", "--extract-json-group", "1"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["result"]["extracted_json"]["correlation_id"], "id-1")
        self.assertNotIn("diagnostics", payload)

    def test_wait_for_log_pattern_extract_modes_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit) as exc:
            unity_puer_exec.run_cli(
                [
                    "wait-for-log-pattern",
                    "--pattern",
                    r"\[Build\] complete",
                    "--extract-group",
                    "0",
                    "--extract-json-group",
                    "1",
                ]
            )

        self.assertEqual(exc.exception.code, 2)

    def test_exec_reads_file_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    unity_puer_exec.EXIT_RUNNING,
                    json.dumps({"ok": True, "status": "running", "request_id": "req-running", "log_offset": 12345, "result": {"correlation_id": "id-7"}}),
                    "",
                ),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--include-log-offset"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["code"], "export default function run(ctx) { return 7; }")
        self.assertTrue(payload["request_id"])
        self.assertTrue(payload["include_log_offset"])
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["request_id"], "req-running")
        self.assertEqual(body["log_offset"], 12345)
        self.assertEqual(body["result"]["correlation_id"], "id-7")

    def test_exec_forwards_explicit_request_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed", "request_id": "req-explicit"}), ""),
            ) as invoke_command:
                unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--request-id", "req-explicit"])

        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["request_id"], "req-explicit")

    def test_exec_include_diagnostics_is_forwarded_and_preserved_top_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    0,
                    json.dumps({"ok": True, "status": "completed", "request_id": "req-7", "diagnostics": {"transport": "debug"}}),
                    "",
                ),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--file", str(script_path), "--include-diagnostics"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = invoke_command.call_args.args[2]
        self.assertTrue(payload["include_diagnostics"])
        body = json.loads(stdout)
        self.assertEqual(body["diagnostics"]["transport"], "debug")

    def test_exec_forwards_unity_log_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ) as ensure_session_ready, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed"}), ""),
            ):
                unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--unity-log-path", "X:/Logs/Editor.log"])

        self.assertEqual(ensure_session_ready.call_args.kwargs["unity_log_path"], "X:/Logs/Editor.log")

    def test_exec_completed_response_preserves_top_level_log_offset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return { correlation_id: 'id-8' }; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "ok": True,
                            "status": "completed",
                            "request_id": "req-8",
                            "log_offset": 67890,
                            "result": {"correlation_id": "id-8"},
                        }
                    ),
                    "",
                ),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--include-log-offset"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["request_id"], "req-8")
        self.assertEqual(body["log_offset"], 67890)
        self.assertEqual(body["result"]["correlation_id"], "id-8")

    def test_exec_hides_diagnostics_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return { correlation_id: 'id-8' }; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    0,
                    json.dumps({"ok": True, "status": "completed", "request_id": "req-9", "diagnostics": {"transport": "debug"}}),
                    "",
                ),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertNotIn("diagnostics", body)
        self.assertEqual(body["request_id"], "req-9")

    def test_exec_timeout_payload_preserves_request_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    unity_puer_exec.EXIT_NOT_AVAILABLE,
                    json.dumps({"ok": False, "status": "not_available", "request_id": "req-timeout", "error": "timed out"}),
                    "",
                ),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--request-id", "req-timeout"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["request_id"], "req-timeout")
        self.assertEqual(body["status"], "not_available")

    def test_exec_startup_not_ready_returns_running_with_next_step_and_persists_pending_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            session = _make_session(project_path=str(project_path))
            not_ready = unity_session.UnityNotReadyError("still starting", session=session)

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=not_ready,
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-start"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-start")
            self.assertEqual(body["next_step"]["command"], "wait-for-exec")
            self.assertIn("wait-for-exec", body["next_step"]["argv"])
            self.assertIn("req-start", body["next_step"]["argv"])
            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-start")
            self.assertEqual(pending["request_id"], "req-start")
            self.assertIn("return 7", pending["code"])
            self.assertFalse(pending["refresh_before_exec"])

    def test_exec_refresh_before_exec_runs_internal_refresh_then_user_exec(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-refresh-refresh", "result": {"refreshed": True}}), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-refresh", "result": {"value": 7}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh", "--refresh-before-exec"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(invoke_command.call_count, 2)
            self.assertEqual(invoke_command.call_args_list[0].args[0], "exec")
            self.assertEqual(invoke_command.call_args_list[0].args[2]["request_id"], "req-refresh-refresh")
            self.assertIn("AssetDatabase.Refresh", invoke_command.call_args_list[0].args[2]["code"])
            self.assertEqual(invoke_command.call_args_list[1].args[2]["request_id"], "req-refresh")
            self.assertIn("return 7", invoke_command.call_args_list[1].args[2]["code"])
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-refresh"))

    def test_exec_refresh_before_exec_returns_running_with_refresh_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps({"ok": True, "status": "running", "request_id": "req-refresh-refresh"}), ""),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh", "--refresh-before-exec"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-refresh")
            self.assertEqual(body["phase"], "refreshing")
            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-refresh")
            self.assertEqual(pending["phase"], "refreshing")
            self.assertEqual(pending["refresh_request_id"], "req-refresh-refresh")

    def test_exec_refresh_before_exec_normalizes_compile_to_running_with_compile_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-refresh-refresh", "result": {"refreshed": True}}), ""),
                    (unity_puer_exec.EXIT_COMPILING, json.dumps({"ok": False, "status": "compiling"}), ""),
                ],
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh", "--refresh-before-exec"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-refresh")
            self.assertEqual(body["phase"], "compiling")
            self.assertEqual(body["next_step"]["command"], "wait-for-exec")
            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-refresh")
            self.assertEqual(pending["phase"], "compiling")
            self.assertEqual(pending["request_id"], "req-refresh")

    def test_wait_for_exec_invokes_follow_up_surface(self):
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            return_value=_make_session(),
        ), mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps({"ok": True, "status": "running", "request_id": "req-follow"}), ""),
        ) as invoke_command:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--request-id", "req-follow"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        self.assertEqual(invoke_command.call_args.args[0], "wait-for-exec")
        self.assertEqual(invoke_command.call_args.args[2]["request_id"], "req-follow")
        body = json.loads(stdout)
        self.assertEqual(body["request_id"], "req-follow")

    def test_wait_for_exec_replays_pending_exec_after_project_becomes_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {"request_id": "req-pending", "code": "export default function run(ctx) { return 11; }"},
            )
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed", "request_id": "req-pending", "result": {"value": 11}}), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(invoke_command.call_args.args[0], "exec")
            payload = invoke_command.call_args.args[2]
            self.assertEqual(payload["request_id"], "req-pending")
            self.assertIn("return 11", payload["code"])
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-pending"))

    def test_wait_for_exec_continues_refresh_phase_then_replays_user_exec(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "refresh_before_exec": True,
                    "phase": "refreshing",
                    "refresh_request_id": "req-pending-refresh",
                },
            )
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-pending-refresh", "result": {"refreshed": True}}), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-pending", "result": {"value": 11}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(invoke_command.call_args_list[0].args[0], "wait-for-exec")
            self.assertEqual(invoke_command.call_args_list[0].args[2]["request_id"], "req-pending-refresh")
            self.assertEqual(invoke_command.call_args_list[1].args[0], "exec")
            self.assertEqual(invoke_command.call_args_list[1].args[2]["request_id"], "req-pending")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-pending"))

    def test_wait_for_exec_keeps_running_during_refresh_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "refresh_before_exec": True,
                    "phase": "refreshing",
                    "refresh_request_id": "req-pending-refresh",
                },
            )
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps({"ok": True, "status": "running", "request_id": "req-pending-refresh"}), ""),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-pending")
            self.assertEqual(body["phase"], "refreshing")

    def test_wait_for_exec_keeps_running_while_pending_compile_phase_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "refresh_before_exec": True,
                    "phase": "compiling",
                    "refresh_request_id": "req-pending-refresh",
                },
            )
            session = _make_session(project_path=str(project_path))
            stalled = unity_session.UnityStalledError("compiling", session=session)

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=stalled,
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-pending")
            self.assertEqual(body["phase"], "compiling")
            self.assertEqual(body["next_step"]["command"], "wait-for-exec")

    def test_wait_for_exec_retries_pending_compile_phase_and_clears_pending_on_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "refresh_before_exec": True,
                    "phase": "compiling",
                    "refresh_request_id": "req-pending-refresh",
                },
            )
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed", "request_id": "req-pending", "result": {"value": 11}}), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(invoke_command.call_args.args[0], "exec")
            self.assertEqual(invoke_command.call_args.args[2]["request_id"], "req-pending")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-pending"))

    def test_wait_for_exec_keeps_running_while_pending_startup_is_still_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {"request_id": "req-pending", "code": "export default function run(ctx) { return 11; }"},
            )
            session = _make_session(project_path=str(project_path))
            stalled = unity_session.UnityStalledError("starting", session=session)

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=stalled,
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            self.assertEqual(body["request_id"], "req-pending")
            self.assertEqual(body["next_step"]["command"], "wait-for-exec")

    def test_exec_timeout_normalizes_supported_modal_blocker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    unity_puer_exec.EXIT_NOT_AVAILABLE,
                    json.dumps({"ok": False, "status": "not_available", "request_id": "req-timeout", "error": "timed out"}),
                    "",
                ),
            ), mock.patch.object(
                unity_puer_exec_runtime.unity_modal_blockers,
                "detect_modal_blocker",
                return_value={"type": "save_scene_dialog", "scope": "exec"},
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path), "--request-id", "req-timeout"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_MODAL_BLOCKED)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        self.assertEqual(body["request_id"], "req-timeout")
        self.assertEqual(body["blocker"]["type"], "save_scene_dialog")

    def test_wait_for_exec_running_normalizes_supported_modal_blocker(self):
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            return_value=_make_session(),
        ), mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps({"ok": True, "status": "running", "request_id": "req-follow"}), ""),
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "detect_modal_blocker",
            return_value={"type": "save_modified_scenes_prompt", "scope": "exec"},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--request-id", "req-follow"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_MODAL_BLOCKED)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        self.assertEqual(body["blocker"]["type"], "save_modified_scenes_prompt")

    def test_get_blocker_state_reports_no_blocker(self):
        with mock.patch.object(unity_session, "get_blocker_state", return_value=_make_session()), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "detect_modal_blocker",
            return_value=None,
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-blocker-state"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["operation"], "get-blocker-state")
        self.assertEqual(body["result"]["status"], "no_blocker")

    def test_get_blocker_state_reports_supported_modal_blocker(self):
        with mock.patch.object(unity_session, "get_blocker_state", return_value=_make_session()), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "detect_modal_blocker",
            return_value={"type": "save_scene_dialog", "scope": "exec"},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-blocker-state"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "modal_blocked")
        self.assertEqual(body["result"]["blocker"]["type"], "save_scene_dialog")

    def test_resolve_blocker_help_renders_cancel_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["resolve-blocker", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("dismissing a supported Unity modal blocker", stdout)
        self.assertIn("resolve-blocker --project-path X:/project --action cancel", stdout)

    def test_resolve_blocker_help_status_mentions_resolution_states(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["resolve-blocker", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`no_supported_blocker` -> exit 1", stdout)
        self.assertIn("`resolution_failed` -> exit 1", stdout)

    def test_resolve_blocker_requires_windows_project_path_surface(self):
        with mock.patch.object(unity_puer_exec_runtime.sys, "platform", "linux"):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["resolve-blocker", "--action", "cancel"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unsupported_operation")
        self.assertEqual(body["error"], "windows_project_path_required")

    def test_resolve_blocker_reports_no_supported_blocker(self):
        with mock.patch.object(unity_puer_exec_runtime.sys, "platform", "win32"), mock.patch.object(
            unity_session, "get_blocker_state", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            return_value={"ok": False, "status": "no_supported_blocker"},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["resolve-blocker", "--project-path", SAMPLE_PROJECT_PATH, "--action", "cancel"]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "no_supported_blocker")
        self.assertEqual(body["operation"], "resolve-blocker")

    def test_resolve_blocker_reports_multiple_supported_blockers(self):
        with mock.patch.object(unity_puer_exec_runtime.sys, "platform", "win32"), mock.patch.object(
            unity_session, "get_blocker_state", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            return_value={"ok": False, "status": "resolution_failed", "error": "multiple_supported_blockers"},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["resolve-blocker", "--project-path", SAMPLE_PROJECT_PATH, "--action", "cancel"]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "resolution_failed")
        self.assertEqual(body["error"], "multiple_supported_blockers")

    def test_resolve_blocker_reports_click_not_confirmed(self):
        with mock.patch.object(unity_puer_exec_runtime.sys, "platform", "win32"), mock.patch.object(
            unity_session, "get_blocker_state", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            return_value={
                "ok": False,
                "status": "resolution_failed",
                "action": "cancel",
                "blocker": {"type": "save_scene_dialog"},
                "error": "click_not_confirmed",
            },
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["resolve-blocker", "--project-path", SAMPLE_PROJECT_PATH, "--action", "cancel"]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "resolution_failed")
        self.assertEqual(body["action"], "cancel")
        self.assertEqual(body["blocker"]["type"], "save_scene_dialog")
        self.assertEqual(body["error"], "click_not_confirmed")

    def test_resolve_blocker_returns_resolved_payload(self):
        with mock.patch.object(unity_puer_exec_runtime.sys, "platform", "win32"), mock.patch.object(
            unity_session, "get_blocker_state", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            return_value={
                "ok": True,
                "status": "completed",
                "result": {
                    "status": "resolved",
                    "action": "cancel",
                    "blocker": {"type": "save_scene_dialog"},
                },
            },
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["resolve-blocker", "--project-path", SAMPLE_PROJECT_PATH, "--action", "cancel"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["operation"], "resolve-blocker")
        self.assertEqual(body["result"]["status"], "resolved")
        self.assertEqual(body["result"]["action"], "cancel")
        self.assertEqual(body["result"]["blocker"]["type"], "save_scene_dialog")

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
        self.assertNotIn("diagnostics", payload)

    def test_get_log_source_forwards_unity_log_path(self):
        session = _make_session()
        result = {"status": "log_source_available", "source": "file", "path": "X:/Logs/Editor.log"}

        with mock.patch.object(unity_session, "get_log_source", return_value=(session, result)) as get_log_source:
            unity_puer_exec.run_cli(["get-log-source", "--project-path", "X:/project", "--unity-log-path", "X:/Logs/Editor.log"])

        self.assertEqual(get_log_source.call_args.kwargs["unity_log_path"], "X:/Logs/Editor.log")

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

    def test_wait_for_result_marker_returns_matching_marker(self):
        session = _make_session()
        first = _make_session()
        first.diagnostics["matched_log_pattern"] = unity_puer_exec.RESULT_MARKER_PATTERN
        first.diagnostics["matched_log_text"] = '[UnityPuerExecResult] {"correlation_id":"other"}'
        first.diagnostics["matched_log_offset"] = 100
        first.diagnostics["extracted_group"] = '{"correlation_id":"other"}'
        session.diagnostics["matched_log_pattern"] = unity_puer_exec.RESULT_MARKER_PATTERN
        session.diagnostics["matched_log_text"] = '[UnityPuerExecResult] {"correlation_id":"wanted","value":9}'
        session.diagnostics["matched_log_offset"] = 150
        session.diagnostics["extracted_group"] = '{"correlation_id":"wanted","value":9}'

        with mock.patch.object(unity_session, "create_observation_session", return_value=first), mock.patch.object(
            unity_session, "wait_for_log_pattern", side_effect=[first, session]
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-result-marker", "--correlation-id", "wanted", "--start-offset", "10"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["result"]["status"], "result_marker_matched")
        self.assertEqual(payload["result"]["marker"]["correlation_id"], "wanted")
        self.assertNotIn("diagnostics", payload["result"])

    def test_wait_for_result_marker_include_diagnostics_returns_top_level_diagnostics(self):
        session = _make_session()
        session.diagnostics["matched_log_pattern"] = unity_puer_exec.RESULT_MARKER_PATTERN
        session.diagnostics["matched_log_text"] = '[UnityPuerExecResult] {"correlation_id":"wanted","value":9}'
        session.diagnostics["matched_log_offset"] = 150
        session.diagnostics["extracted_group"] = '{"correlation_id":"wanted","value":9}'

        with mock.patch.object(unity_session, "create_observation_session", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-result-marker", "--correlation-id", "wanted", "--include-diagnostics"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["diagnostics"]["matched_log_pattern"], unity_puer_exec.RESULT_MARKER_PATTERN)
        self.assertEqual(payload["diagnostics"]["matched_log_text"], '[UnityPuerExecResult] {"correlation_id":"wanted","value":9}')

    def test_wait_for_result_marker_maps_session_guard_failure(self):
        session = _make_session()
        error = unity_session.UnitySessionStateError("session_stale", "stale", session=session)

        with mock.patch.object(unity_session, "create_observation_session", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", side_effect=error
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-result-marker", "--correlation-id", "wanted", "--expected-session-marker", "marker-1"]
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_SESSION_STATE)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "session_stale")

    def test_wait_for_log_pattern_forwards_unity_log_path(self):
        session = _make_session()
        with mock.patch.object(unity_session, "create_observation_session", return_value=session) as create_observation_session, mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            unity_puer_exec.run_cli(
                [
                    "wait-for-log-pattern",
                    "--project-path",
                    "X:/project",
                    "--pattern",
                    r"\[Build\] complete",
                    "--unity-log-path",
                    "X:/Logs/Editor.log",
                ]
            )

        self.assertEqual(create_observation_session.call_args.kwargs["unity_log_path"], "X:/Logs/Editor.log")

    def test_wait_for_result_marker_forwards_unity_log_path(self):
        session = _make_session()
        session.diagnostics["matched_log_offset"] = 150
        session.diagnostics["extracted_group"] = '{"correlation_id":"wanted"}'
        with mock.patch.object(unity_session, "create_observation_session", return_value=session) as create_observation_session, mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ):
            unity_puer_exec.run_cli(
                [
                    "wait-for-result-marker",
                    "--project-path",
                    "X:/project",
                    "--correlation-id",
                    "wanted",
                    "--unity-log-path",
                    "X:/Logs/Editor.log",
                ]
            )

        self.assertEqual(create_observation_session.call_args.kwargs["unity_log_path"], "X:/Logs/Editor.log")

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

    def test_launch_conflict_maps_to_exit_code_20(self):
        session = _make_session()
        error = unity_session.UnityLaunchConflictError("launch ownership conflict", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-until-ready"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_START_FAILED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "launch_conflict")
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
