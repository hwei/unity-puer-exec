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
import unity_session_common  # type: ignore
import unity_session_logs  # type: ignore
import help_surface  # type: ignore

from tests import version_test_support


SAMPLE_PROJECT_PATH = "X:/unity-project"

_bridge_probe_patcher = None


def setUpModule():
    """Keep the base-url bridge guard from reaching a real local Editor.

    These cases mock the command transport and assume nothing answers on the
    loopback control ports. The bridge guard added a real `/health` probe on that
    path, which would otherwise make the results depend on whether the developer
    happens to have Unity open. The guard's own behavior is covered by
    tests.test_cli_version.
    """
    global _bridge_probe_patcher
    _bridge_probe_patcher = mock.patch.object(
        unity_session, "probe_health_payload", return_value=(None, "no service")
    )
    _bridge_probe_patcher.start()


def tearDownModule():
    if _bridge_probe_patcher is not None:
        _bridge_probe_patcher.stop()


def _expand_brief_sequence(sequence):
    expanded = []
    i = 0
    while i < len(sequence):
        symbol = sequence[i]
        i += 1
        count_start = i
        while i < len(sequence) and sequence[i].isdigit():
            i += 1
        count = int(sequence[count_start:i]) if i > count_start else 1
        expanded.append(symbol * count)
    return "".join(expanded)


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
    def test_parser_exposes_formal_command_tree_without_wait_until_ready(self):
        import unity_puer_exec_surface as surface

        parser = unity_puer_exec._build_parser()
        args = parser.parse_args(["wait-for-exec", "--request-id", "req-1"])
        self.assertEqual(args.command, "wait-for-exec")
        with self.assertRaises(surface.ArgumentParseError):
            parser.parse_args(["wait-until-ready"])

    def test_exec_parser_accepts_import_base_url_and_reset_jsenv_before_exec(self):
        parser = unity_puer_exec._build_parser()
        args = parser.parse_args(
            ["exec", "--code", "export default function run(ctx) { return 1; }", "--import-base-url", "http://localhost:3000", "--reset-jsenv-before-exec"]
        )

        self.assertEqual(args.command, "exec")
        self.assertEqual(args.import_base_url, "http://localhost:3000")
        self.assertTrue(args.reset_jsenv_before_exec)

    def test_exec_parser_defaults_and_accepts_stale_module_policy(self):
        parser = unity_puer_exec._build_parser()
        default_args = parser.parse_args(["exec", "--code", "export default function run(ctx) { return 1; }"])
        error_args = parser.parse_args([
            "exec", "--code", "export default function run(ctx) { return 1; }",
            "--stale-module-policy", "error",
        ])

        import unity_puer_exec_surface as surface

        self.assertEqual(default_args.stale_module_policy, "auto-reset")
        self.assertEqual(error_args.stale_module_policy, "error")
        with self.assertRaises(surface.ArgumentParseError):
            parser.parse_args([
                "exec", "--code", "export default function run(ctx) { return 1; }",
                "--stale-module-policy", "invalid",
            ])

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
        self.assertIn("Common Help Examples", stdout)
        self.assertIn("get-blocker-state", stdout)
        self.assertIn("exec-and-wait-for-result-marker", stdout)
        self.assertIn("exec-and-wait-for-log-pattern", stdout)
        self.assertIn("load-and-call-csharp-type", stdout)
        self.assertIn("recover-exec-by-request-id", stdout)
        self.assertIn("help-example id for `unity-puer-exec --help-example exec-and-wait-for-log-pattern`", stdout)
        self.assertIn("See `exec --help`.", stdout)
        self.assertIn("start with `exec --project-path ...`", stdout)
        self.assertIn("not the normal first step", stdout)
        self.assertIn("PuerTS-style JavaScript-to-C# bridge", stdout)
        self.assertIn("do not assume bridged C# arrays or `List<T>` values behave exactly like native JS arrays", stdout)
        self.assertIn("`--response-file <path>`", stdout)
        self.assertIn("byte_count", stdout)
        self.assertIn("sha256", stdout)

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
        self.assertIn("Related Help Examples", stdout)
        self.assertIn("`--help-args`", stdout)
        self.assertIn("`--help-status`", stdout)
        self.assertIn("exec-and-wait-for-result-marker", stdout)
        self.assertIn("load-and-call-csharp-type", stdout)
        self.assertIn("use `unity-puer-exec --help-example exec-and-wait-for-result-marker`", stdout)
        self.assertIn("Normal first command for project-scoped work", stdout)
        self.assertIn("owns Unity launch or recovery for the project", stdout)
        self.assertIn("PuerTS-style JavaScript-to-C# bridge", stdout)
        self.assertIn("no action is needed: the next project-scoped `exec` refreshes automatically", stdout)
        self.assertIn("non-code assets are not watched and do not trigger a refresh", stdout)
        self.assertIn("`AssetDatabase.Refresh()` through the bridge", stdout)
        self.assertIn("Continue with `wait-for-exec` if the request stays non-terminal", stdout)
        self.assertIn("Every script source (`--file`, `--stdin`, `--code`) must use this module entry template", stdout)
        self.assertIn("only `ctx.request_id`, `ctx.globals`, and `ctx.args` are guaranteed", stdout)
        self.assertIn("`--help-example derive-project-path-from-unity-api`", stdout)
        self.assertIn("--response-file X:/work/.tmp/result.json", stdout)
        self.assertIn("not the preferred large-result transport", stdout)
        self.assertIn("separate from the host application's own JavaScript runtime", stdout)
        self.assertIn("shared C#/Unity object graph", stdout)
        self.assertIn("place or read shared C#/Unity state both sides can observe", stdout)
        self.assertIn("belongs in a project-local skill", stdout)
        self.assertIn("transition was requested, not completed", stdout)
        self.assertIn("confirm the play state changed", stdout)
        self.assertIn("PowerShell users composing inline `--code`", stdout)
        self.assertIn("JavaScript syntax error that does not name the shell", stdout)

    def test_exec_help_args_renders_argument_template(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Arguments", stdout)
        self.assertIn("Selector Rules", stdout)
        self.assertIn("Bridge Model", stdout)
        self.assertIn("Script Context", stdout)
        self.assertIn("Timeout Rules", stdout)
        self.assertIn("`--file <path>`", stdout)
        self.assertIn("`--code <inline-js>`", stdout)
        self.assertIn("`--request-id <id>`", stdout)
        self.assertIn("Automatic refresh: before each exec the server checks", stdout)
        self.assertIn("not watched and do not trigger a refresh", stdout)
        self.assertIn("`--include-diagnostics`", stdout)
        self.assertIn("`export default function", stdout)
        self.assertIn("Every script source must provide a full module entry", stdout)
        self.assertIn("not a fragment", stdout)
        self.assertIn("Promise", stdout)
        self.assertIn("`puer.loadType(...)`", stdout)
        self.assertIn("Bridged C# arrays and `List<T>` values are not plain JS arrays", stdout)
        self.assertIn("the next `exec` refreshes automatically", stdout)
        self.assertIn("https://puerts.github.io/docs/puerts/unity/tutorial/js2cs", stdout)
        self.assertIn("`ctx.request_id`, `ctx.globals`, and `ctx.args`", stdout)
        self.assertIn("`--script-args <json-object>`", stdout)
        self.assertIn("`ctx.project_path`", stdout)

    def test_exec_help_states_refresh_settle_is_not_bounded_by_wait_timeout(self):
        """`exec --help` must separate the two budgets in the wait/timeout guidance.

        The real-host regression used `WAIT_TIMEOUT_MS = 1000` and had to be repaired
        with a second, compile-scale constant, because help described `--wait-timeout-ms`
        as the whole of "how long to wait". The statement has to survive in the timeout
        rules, not only inside the automatic-refresh description.
        """
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        timeout_rules = stdout.split("Timeout Rules", 1)[1]
        self.assertIn("compile-scale budget of its own", timeout_rules)
        self.assertIn("not bounded by `--wait-timeout-ms`", timeout_rules)
        # The option line itself must not read as the whole budget either.
        wait_line = next(line for line in stdout.splitlines() if line.startswith("- `--wait-timeout-ms"))
        self.assertIn("does not bound the compile cycle an automatic refresh settles on", wait_line)
        # And the automatic-refresh description carries the same fact.
        self.assertIn("not bounded by `--wait-timeout-ms`", stdout)

    def test_exec_help_status_states_refresh_settle_budget_and_lists_the_outcome(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("compile-scale budget of its own", stdout)
        self.assertIn("not on `--wait-timeout-ms`", stdout)
        # The exhausted-budget outcome is a documented non-success status.
        self.assertIn("refresh_unsettled", stdout)
        self.assertIn("25", stdout)

    def test_exec_refresh_unsettled_help_distinguishes_itself_from_missing(self):
        entry = help_surface.COMMAND_HELP["exec"]["status"]["failure"]
        refresh_entry = next(row for row in entry if row[0] == "refresh_unsettled")
        self.assertEqual(refresh_entry[1], help_surface.EXIT_REFRESH_UNSETTLED)
        self.assertIn("has not run", refresh_entry[2])
        self.assertIn("for the first time", refresh_entry[2])
        # `missing` keeps its own distinct meaning, on the wait-for-exec surface.
        wait_entry = help_surface.COMMAND_HELP["wait-for-exec"]["status"]["failure"]
        missing_entry = next(row for row in wait_entry if row[0] == "missing")
        self.assertEqual(missing_entry[1], 13)
        self.assertNotEqual(missing_entry[1], refresh_entry[1])

    def test_exec_help_status_does_not_contradict_wait_for_compile_settle_cycle(self):
        exec_exit, exec_stdout, _ = unity_puer_exec.run_cli(["exec", "--help-args"])
        compile_exit, compile_stdout, _ = unity_puer_exec.run_cli(["wait-for-compile", "--help-args"])

        self.assertEqual(exec_exit, 0)
        self.assertEqual(compile_exit, 0)
        # exec names the very option wait-for-compile exposes for the same cycle.
        self.assertIn("compile-scale budget of its own", exec_stdout)
        self.assertIn("`wait-for-compile --settle-timeout-seconds`", exec_stdout)
        self.assertIn("`--settle-timeout-seconds <seconds>`", compile_stdout)
        self.assertIn("distinct from the settle timeout", compile_stdout)

    def test_refresh_unsettled_guidance_offers_resubmit_and_not_wait_for_exec(self):
        entry = help_surface.GUIDANCE_MATRIX[("exec", "refresh_unsettled")]

        commands = [step["command"] for step in entry["next_steps"]]
        self.assertIn("exec", commands)
        self.assertIn("wait-for-compile", commands)
        self.assertNotIn("wait-for-exec", commands)
        resubmit = next(step for step in entry["next_steps"] if step["command"] == "exec")
        self.assertIn("--base-url", resubmit["argv_template"])
        self.assertIn("--request-id", resubmit["argv_template"])

    def test_exec_running_wait_for_exec_candidate_is_marked_replayable_only(self):
        entry = help_surface.GUIDANCE_MATRIX[("exec", "running")]

        wait_step = next(step for step in entry["next_steps"] if step["command"] == "wait-for-exec")
        self.assertTrue(wait_step["requires_replayable_record"])
        # The other candidates need no such record and stay unmarked.
        for step in entry["next_steps"]:
            if step["command"] != "wait-for-exec":
                self.assertNotIn("requires_replayable_record", step)

    def test_wait_for_exec_help_renders_recovery_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Preferred follow-up", stdout)
        self.assertIn("accepted exec `request_id`", stdout)
        self.assertIn("--response-file X:/work/.tmp/recovered.json` recovers the retained completed response", stdout)
        self.assertIn("without re-running the script", stdout)

    def test_get_log_briefs_help_documents_full_text_and_response_file_composition(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-log-briefs", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`--full-text`", stdout)
        self.assertIn("`--response-file`", stdout)

    def test_get_log_briefs_help_args_documents_full_text_selection_rule(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-log-briefs", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`--full-text`: attach the complete decoded text", stdout)
        self.assertIn("requires explicit indices", stdout)
        self.assertIn("`--full-text` without `--indexes` (or its `--include` alias) is a usage error", stdout)
        self.assertIn("`--response-file <path>`", stdout)

    def test_get_log_briefs_help_status_documents_full_text_usage_error(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-log-briefs", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`full_text_requires_include` -> exit 2", stdout)
        self.assertIn("full_text", stdout)

    def test_wait_for_log_pattern_help_mentions_log_workflow_example(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-log-pattern", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Quick Start", stdout)
        self.assertIn("Related Help Examples", stdout)
        self.assertIn("exec-and-wait-for-log-pattern", stdout)
        self.assertIn("exec-and-wait-for-result-marker", stdout)
        self.assertIn("use `unity-puer-exec --help-example exec-and-wait-for-log-pattern`", stdout)
        self.assertIn("`log_range.start` when waiting for output the originating command itself produced", stdout)
        self.assertIn("`log_range.end` when observing activity that follows it", stdout)
        self.assertIn("guards against matching stale output", stdout)
        self.assertIn("guards against accepting observation from a different Editor session", stdout)
        self.assertIn("complementary", stdout)

    def test_wait_for_log_pattern_help_args_documents_offset_and_session_guards(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-log-pattern", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`--start-offset <offset>`", stdout)
        self.assertIn("`log_range.start` when the awaited output came from the originating command", stdout)
        self.assertIn("`log_range.end` when the awaited activity follows it", stdout)
        self.assertIn("before the intended observation window", stdout)
        self.assertIn("`--expected-session-marker <marker>`", stdout)
        self.assertIn("different Editor session", stdout)
        self.assertIn("Complementary to `--start-offset`", stdout)

    def test_wait_for_exec_help_status_mentions_missing(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`missing` -> exit 13", stdout)
        self.assertIn("expired or malformed local pending leftovers", stdout)
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

    def test_help_example_renders_known_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "exec-and-wait-for-result-marker"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Goal", stdout)
        self.assertIn("Steps", stdout)
        self.assertIn("What To Notice", stdout)
        self.assertIn("correlation_id", stdout)
        self.assertIn("log_range.start", stdout)
        self.assertIn("Do not assume `running` already includes `result.correlation_id`", stdout)

    def test_log_pattern_help_example_renders_checkpointed_workflow(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "exec-and-wait-for-log-pattern"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Goal", stdout)
        self.assertIn("wait-for-log-pattern", stdout)
        self.assertIn("log_range.start", stdout)
        self.assertIn("--start-offset OFFSET", stdout)
        self.assertIn("direct host-log inspection", stdout)
        self.assertIn("produced by that same `exec`", stdout)
        self.assertIn("Use `log_range.end` when observing activity that follows the originating command", stdout)
        self.assertIn("pair it with `--expected-session-marker`", stdout)

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
        self.assertIn("ctx.args", stdout)
        self.assertIn("bridged C# arrays and `List<T>` values", stdout)
        self.assertIn("compile recovery stays attached to that request", stdout)
        self.assertIn("https://puerts.github.io/docs/puerts/unity/tutorial/js2cs", stdout)

    def test_project_path_derivation_help_example_renders_supported_path_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "derive-project-path-from-unity-api"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("supported Unity APIs", stdout)
        self.assertIn("const Application = puer.loadType('UnityEngine.Application');", stdout)
        self.assertIn("const Path = puer.loadType('System.IO.Path');", stdout)
        self.assertIn("Path.GetDirectoryName(Application.dataPath)", stdout)
        self.assertIn("`ctx.project_path`", stdout)

    def test_component_detection_help_example_renders_static_access_vs_typeof_distinction(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help-example", "component-detection"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(
            "const scene = CS.UnityEngine.SceneManagement.SceneManager.GetActiveScene();",
            stdout,
        )
        self.assertNotIn("puer.$typeof(CS.UnityEngine.SceneManagement.SceneManager)", stdout)
        self.assertIn("puer.$typeof(CS.UnityEngine.MeshFilter), mf", stdout)
        self.assertIn(
            "only wrap a type in `puer.$typeof(CS.UnityEngine.X)` when a `System.Type` value is required as a parameter",
            stdout,
        )
        self.assertIn("get_Item(i)", stdout)
        self.assertIn("puer.$ref()", stdout)

    def test_exec_help_describes_running_without_immediate_correlation_id_guarantee(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`running`: the request is still active", stdout)
        self.assertIn("wait-for-exec --request-id", stdout)
        self.assertIn("`refreshing`", stdout)
        self.assertIn("`compiling`", stdout)
        self.assertIn("entry function returned a Promise", stdout)
        self.assertIn("`modal_blocked` -> exit 19", stdout)

    def test_exec_help_describes_stale_module_policy_and_recovery_choices(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-args"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("--stale-module-policy auto-reset|error", stdout)
        self.assertIn("same invocation", stdout)
        self.assertIn("module_cache_stale", stdout)

    def test_stale_module_guidance_contains_explicit_and_auto_reset_candidates(self):
        import help_surface

        entry = help_surface.GUIDANCE_MATRIX[("exec", "module_cache_stale")]
        self.assertIn("--reset-jsenv-before-exec", entry["next_steps"][0]["argv_template"])
        self.assertIn("--stale-module-policy", entry["next_steps"][1]["argv_template"])

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
        with mock.patch.object(unity_session, "create_observation_session") as create_session:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
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

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertEqual(body["command"], "wait-for-log-pattern")
        create_session.assert_not_called()

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
                    json.dumps({"ok": True, "status": "running", "request_id": "req-running", "result": {"correlation_id": "id-7"}}),
                    "",
                ),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path)])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["code"], "export default function run(ctx) { return 7; }")
        self.assertTrue(payload["request_id"])
        self.assertEqual(payload["script_args_json"], "{}")
        self.assertNotIn("include_log_offset", payload)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["request_id"], "req-running")
        self.assertIn("log_range", body)
        self.assertIn("brief_sequence", body)
        self.assertEqual(body["result"]["correlation_id"], "id-7")

    def test_exec_payload_includes_source_path_import_base_url_and_reset_flag(self):
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
                side_effect=[
                    (0, json.dumps({"ok": True, "status": "completed"}), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-import", "result": {"value": 7}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    [
                        "exec",
                        "--file",
                        str(script_path),
                        "--request-id",
                        "req-import",
                        "--import-base-url",
                        "http://localhost:3000",
                        "--reset-jsenv-before-exec",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(len(invoke_command.call_args_list), 1)
        self.assertEqual(invoke_command.call_args_list[0].args[0], "exec")
        payload = invoke_command.call_args_list[0].args[2]
        self.assertEqual(payload["request_id"], "req-import")
        self.assertEqual(payload["source_path"], os.path.abspath(script_path))
        self.assertEqual(payload["import_base_url"], "http://localhost:3000")
        self.assertTrue(payload["reset_jsenv_before_exec"])
        self.assertEqual(payload["stale_module_policy"], "auto-reset")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")

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
                unity_puer_exec.run_cli(
                    ["exec", "--file", str(script_path), "--request-id", "req-explicit", "--script-args", '{"b":2,"a":1}']
                )

        payload = invoke_command.call_args.args[2]
        self.assertEqual(payload["request_id"], "req-explicit")
        self.assertEqual(payload["script_args_json"], '{"a":1,"b":2}')

    def test_exec_rejects_malformed_script_args_before_runtime(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--code", "export default function run(ctx) { return 1; }", "--script-args", "{bad"]
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "invalid_script_args_json")

    def test_exec_rejects_non_object_script_args_before_runtime(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--code", "export default function run(ctx) { return 1; }", "--script-args", "[1,2,3]"]
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "invalid_script_args_type")

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

    def test_exec_completed_response_includes_log_range(self):
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
                            "result": {"correlation_id": "id-8"},
                        }
                    ),
                    "",
                ),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--file", str(script_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["request_id"], "req-8")
        self.assertIn("log_range", body)
        self.assertIn("start", body["log_range"])
        self.assertIn("end", body["log_range"])
        self.assertIn("brief_sequence", body)
        self.assertEqual(body["result"]["correlation_id"], "id-8")

    def test_exec_bare_typeof_reference_error_gets_puer_prefix_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-typeof",
            "error": "ReferenceError: $typeof is not defined",
        }
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { return $typeof; }",
                    "--request-id", "R-typeof",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertIn("puer.$typeof", body["situation"])
        self.assertNotIn("next_steps", body)

    def test_exec_bare_ref_reference_error_gets_puer_prefix_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-ref",
            "error": "ReferenceError: $ref is not defined",
        }
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { return $ref; }",
                    "--request-id", "R-ref",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertIn("puer.$ref", body["situation"])
        self.assertNotIn("next_steps", body)

    def test_exec_unrelated_failure_does_not_get_puer_prefix_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-unrelated",
            "error": "TypeError: Cannot read properties of undefined (reading 'foo')",
        }
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { return ctx.args.foo.bar; }",
                    "--request-id", "R-unrelated",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertNotIn("puer.$typeof", body["situation"])
        self.assertNotIn("puer.$ref", body["situation"])

    def test_exec_application_error_mentioning_typeof_in_prose_does_not_get_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-prose",
            "error": "Error: please use $typeof to resolve this component type",
        }
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { throw new Error('please use $typeof to resolve this component type'); }",
                    "--request-id", "R-prose",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertNotIn("puer.$typeof", body["situation"])

    def test_wait_for_exec_recovers_bare_typeof_failure_with_same_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-recover-typeof",
            "error": "ReferenceError: $typeof is not defined",
        }
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "wait-for-exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--request-id", "R-recover-typeof",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertIn("puer.$typeof", body["situation"])
        self.assertNotIn("next_steps", body)

    def test_exec_shell_expansion_syntax_error_gets_hint_for_code_source(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-shell-expand",
            "error": "SyntaxError: Unexpected token '('",
        }
        expanded_code = "export default function run(ctx) { return puer.($typeof); }"
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ) as invoke:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", expanded_code,
                    "--request-id", "R-shell-expand",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertIn("shell expanded", body["situation"])
        self.assertIn("single quotes", body["situation"])
        self.assertIn("--file", body["situation"])
        invoke.assert_called_once()

    def test_exec_ordinary_syntax_error_does_not_get_shell_expansion_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-syntax",
            "error": "SyntaxError: Unexpected token '{'",
        }
        ordinary_code = "export default function run(ctx) { return {; }"
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(1, "", json.dumps(failure_body)),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", ordinary_code,
                    "--request-id", "R-syntax",
                ]
            )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertNotIn("shell expanded", body.get("situation", ""))

    def test_exec_file_syntax_error_does_not_get_shell_expansion_hint(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-file-syntax",
            "error": "SyntaxError: Unexpected token '('",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text(
                "export default function run(ctx) { return puer.($typeof); }",
                encoding="utf-8",
            )
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(1, "", json.dumps(failure_body)),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    [
                        "exec",
                        "--base-url", "http://127.0.0.1:55231",
                        "--file", str(script_path),
                        "--request-id", "R-file-syntax",
                    ]
                )

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertNotIn("shell expanded", body.get("situation", ""))

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

    def test_exec_empty_response_body_is_a_named_branchable_state(self):
        class MalformedBodyTransport:
            def post_json(self, url, payload, timeout_seconds):
                raise json.JSONDecodeError("Expecting value", "", 0)

        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "HttpTransport",
            MalformedBodyTransport,
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url",
                    "http://127.0.0.1:55231",
                    "--code",
                    "export default function run(ctx) { return 1; }",
                    "--request-id",
                    "req-empty",
                ]
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "empty_response")
        self.assertEqual(body["operation"], "exec")
        self.assertEqual(body["request_id"], "req-empty")
        self.assertNotIn("Expecting value", body["error"])
        self.assertIn("Expecting value", body["response_detail"]["decode_error"])
        self.assertEqual(
            body["exit_code_meaning"],
            unity_puer_exec.direct_exec_client.EMPTY_RESPONSE_EXIT_MEANING,
        )
        self.assertTrue(body["next_steps"])
        failure_statuses = [item[0] for item in help_surface.COMMAND_HELP["exec"]["status"]["failure"]]
        self.assertIn("empty_response", failure_statuses)

    def test_exec_genuine_process_failure_still_exits_failed_and_stays_distinct(self):
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            side_effect=RuntimeError("unexpected boom"),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url",
                    "http://127.0.0.1:55231",
                    "--code",
                    "export default function run(ctx) { return 1; }",
                    "--request-id",
                    "req-boom",
                ]
            )

        # The named empty-response state must not absorb a genuinely unexpected
        # process-level failure: that still exits 1 with status failed.
        self.assertEqual(exit_code, 1)
        body = json.loads(stdout or stderr)
        self.assertEqual(body["status"], "failed")
        self.assertNotEqual(body["status"], unity_puer_exec.direct_exec_client.STATUS_EMPTY_RESPONSE)

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
            self.assertEqual(body["next_steps"][0]["command"], "wait-for-exec")
            self.assertIn("wait-for-exec", body["next_steps"][0]["argv"])
            self.assertIn("req-start", body["next_steps"][0]["argv"])
            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-start")
            self.assertEqual(pending["request_id"], "req-start")
            self.assertIn("return 7", pending["code"])
            self.assertEqual(pending["script_args"], {})
            self.assertEqual(pending["script_args_json"], "{}")
            self.assertNotIn("refresh_before_exec", pending)
            self.assertEqual(pending["schema_version"], 2)
            self.assertIn("created_at_ms", pending)
            self.assertIn("updated_at_ms", pending)

    def test_exec_removed_refresh_flag_raises_usage_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh", "--refresh-before-exec"]
                )

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout, "")
            body = json.loads(stderr)
            self.assertEqual(body["status"], "removed_refresh_flag")
            self.assertIn("--refresh-before-exec has been removed", body["error"])
            self.assertNotIn("unrecognized", body["error"])
            # The situation names the removal and the automatic replacement.
            self.assertIn("situation", body)
            self.assertIn("Refresh is now automatic", body["situation"])
            # No exec was submitted and no pending request was recorded.
            self.assertEqual(invoke_command.call_count, 0)
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-refresh"))

    def test_exec_automatic_refresh_settles_then_runs_user_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-refresh",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": ["C:/Project/Assets/A.cs"],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 3,
                },
            }
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ) as ensure, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-refresh", "result": {"value": 7}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh"]
                )

            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-refresh")

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        # The first submit triggered the refresh; the second re-used the same request_id
        # so the terminal response carries the script result, not a refresh confirmation.
        self.assertEqual(invoke_command.call_count, 2)
        self.assertNotIn("refresh_before_exec", invoke_command.call_args_list[0].args[2])
        self.assertEqual(invoke_command.call_args_list[0].args[2]["request_id"], "req-refresh")
        self.assertEqual(invoke_command.call_args_list[1].args[2]["request_id"], "req-refresh")
        self.assertIn("return 7", invoke_command.call_args_list[1].args[2]["code"])
        # One ensure_session_ready up front, one to settle the refresh-triggered compile.
        self.assertEqual(ensure.call_count, 2)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["value"], 7)
        self.assertTrue(body["refresh"]["triggered"])
        self.assertEqual(body["refresh"]["paths_changed"], ["C:/Project/Assets/A.cs"])
        self.assertIsNone(pending)

    def test_exec_automatic_refresh_reports_running_when_settle_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            session = _make_session(project_path=str(project_path))
            not_ready = unity_session.UnityNotReadyError("still compiling", session=session)
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-refresh",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": [],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 2,
                },
            }
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=[session, not_ready],
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh"]
                )

            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-refresh")

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        # The refresh phase did not settle, so the request stays non-terminal and no
        # second submit is attempted.
        self.assertEqual(invoke_command.call_count, 1)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["request_id"], "req-refresh")
        self.assertEqual(body["phase"], "refreshing")
        self.assertTrue(body["refresh"]["triggered"])
        self.assertEqual(pending["phase"], "refreshing")

    def test_exec_automatic_refresh_settle_then_compile_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-refresh",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": [],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 2,
                },
            }
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
                    (unity_puer_exec.EXIT_COMPILING, json.dumps({"ok": False, "status": "compiling"}), ""),
                ],
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path), "--request-id", "req-refresh"]
                )

            pending = unity_session.read_pending_exec_artifact(str(project_path), "req-refresh")

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["request_id"], "req-refresh")
        self.assertEqual(body["phase"], "compiling")
        self.assertEqual(body["next_steps"][0]["command"], "wait-for-exec")
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
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "script_args": {"value": 11},
                    "script_args_json": "{\"value\":11}",
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
            payload = invoke_command.call_args.args[2]
            self.assertEqual(payload["request_id"], "req-pending")
            self.assertIn("return 11", payload["code"])
            self.assertEqual(payload["script_args_json"], "{\"value\":11}")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-pending"))

    def test_wait_for_exec_replays_pending_exec_with_import_context_and_reset_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "source_path": "C:/scripts/entry.js",
                    "import_base_url": "http://localhost:3000",
                    "reset_jsenv_before_exec": True,
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
                    (0, json.dumps({"ok": True, "status": "completed"}), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-pending", "result": {"value": 11}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(invoke_command.call_args_list[0].args[0], "exec")
        payload = invoke_command.call_args_list[0].args[2]
        self.assertEqual(payload["source_path"], "C:/scripts/entry.js")
        self.assertEqual(payload["import_base_url"], "http://localhost:3000")
        self.assertTrue(payload["reset_jsenv_before_exec"])
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")

    def test_wait_for_exec_settles_refresh_phase_then_replays_user_exec(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "script_args": {"value": 11},
                    "script_args_json": "{\"value\":11}",
                    "phase": "refreshing",
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
            # The refresh phase settles in-process, then the user exec replays under the
            # same request_id; there is no separate refresh request to wait on.
            self.assertEqual(invoke_command.call_count, 1)
            self.assertEqual(invoke_command.call_args.args[0], "exec")
            self.assertEqual(invoke_command.call_args.args[2]["request_id"], "req-pending")
            self.assertEqual(invoke_command.call_args.args[2]["script_args_json"], "{\"value\":11}")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "completed")
            self.assertIsNone(unity_session.read_pending_exec_artifact(str(project_path), "req-pending"))

    def test_wait_for_exec_keeps_running_while_refresh_phase_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "req-pending",
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "script_args": {},
                    "script_args_json": "{}",
                    "phase": "refreshing",
                },
            )
            session = _make_session(project_path=str(project_path))
            not_ready = unity_session.UnityNotReadyError("compiling", session=session)
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=not_ready,
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
                    "script_args": {},
                    "script_args_json": "{}",
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
            self.assertEqual(body["next_steps"][0]["command"], "wait-for-exec")

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
                    "script_args": {},
                    "script_args_json": "{}",
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
                {
                    "request_id": "req-pending",
                    "code": "export default function run(ctx) { return 11; }",
                    "script_args": {},
                    "script_args_json": "{}",
                },
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
            self.assertEqual(body["next_steps"][0]["command"], "wait-for-exec")

    def test_wait_for_exec_refreshes_pending_timestamp_while_request_remains_recoverable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            with mock.patch.object(unity_session_logs.time, "time", return_value=100.0):
                unity_session.write_pending_exec_artifact(
                    str(project_path),
                    "req-pending",
                    {
                        "request_id": "req-pending",
                        "code": "export default function run(ctx) { return 11; }",
                        "script_args": {},
                        "script_args_json": "{}",
                    },
                )
            session = _make_session(project_path=str(project_path))
            stalled = unity_session.UnityStalledError("starting", session=session)

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                side_effect=stalled,
            ), mock.patch.object(unity_session_logs.time, "time", return_value=150.0):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-pending"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "running")
            with mock.patch.object(unity_session_logs.time, "time", return_value=150.0):
                pending = unity_session.read_pending_exec_artifact(str(project_path), "req-pending")
            self.assertEqual(pending["created_at_ms"], 100000)
            self.assertEqual(pending["updated_at_ms"], 150000)

    def test_wait_for_exec_expired_pending_artifact_is_cleaned_and_missing_is_returned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            artifact_path = unity_session_logs.pending_exec_artifact_path(str(project_path), "req-expired")
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "request_id": "req-expired",
                        "code": "export default function run(ctx) { return 11; }",
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
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_MISSING, json.dumps({"ok": False, "status": "missing", "request_id": "req-expired"}), ""),
            ) as invoke_command, mock.patch.object(unity_session_logs.time, "time", return_value=expired_at):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "req-expired"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_MISSING)
            self.assertEqual(stderr, "")
            self.assertEqual(invoke_command.call_args.args[0], "wait-for-exec")
            body = json.loads(stdout)
            self.assertEqual(body["status"], "missing")
            self.assertFalse(artifact_path.exists())

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

    def test_safe_mode_compile_error_shape_is_stable_without_log_matches(self):
        session = _make_session()
        stdout_text = json.dumps({"ok": True, "status": "running", "request_id": "req-safe"})
        with mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "detect_modal_blocker",
            return_value={"type": "safe_mode_dialog", "scope": "exec"},
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            return_value={"ok": True, "status": "completed"},
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_extract_compile_errors_from_log",
            return_value=None,
        ):
            exit_code, stdout, stderr = unity_puer_exec_runtime._normalize_exec_blocker_result(
                unity_puer_exec.EXIT_RUNNING,
                stdout_text,
                "",
                session,
                log_path="Editor.log",
            )

        self.assertEqual(exit_code, unity_puer_exec.direct_exec_client.EXIT_UNITY_COMPILE_ERROR)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_compile_error")
        self.assertEqual(body["request_id"], "req-safe")
        self.assertEqual(body["compile_errors_total"], 0)
        self.assertEqual(body["compile_warnings_total"], 0)
        self.assertEqual(body["compile_messages"], [])

    def test_unknown_modal_dialog_is_reported_and_never_auto_dismissed(self):
        """An unknown dialog blocks with EXIT_MODAL_BLOCKED and no automatic action."""
        session = _make_session()
        stdout_text = json.dumps({"ok": True, "status": "running", "request_id": "req-unknown"})
        blocker = {"type": "unknown_modal_dialog", "scope": "exec", "hwnd": 42}
        with mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "detect_modal_blocker",
            return_value=blocker,
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "resolve_modal_blocker",
            side_effect=AssertionError("must not auto-dismiss an unknown dialog"),
        ) as resolve_mock:
            exit_code, stdout, stderr = unity_puer_exec_runtime._normalize_exec_blocker_result(
                unity_puer_exec.EXIT_RUNNING,
                stdout_text,
                "",
                session,
                log_path="Editor.log",
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_MODAL_BLOCKED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        self.assertEqual(body["blocker"]["type"], "unknown_modal_dialog")
        self.assertEqual(body["blocker"]["scope"], "exec")
        resolve_mock.assert_not_called()

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

    def test_resolve_blocker_help_renders_click_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["resolve-blocker", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("dismissing a reported Unity modal blocker", stdout)
        self.assertIn("--action click --hwnd <int> --button \"<label>\"", stdout)

    def test_resolve_blocker_help_scopes_cancel_to_safe_mode(self):
        """Cancel must not be advertised as the general unblock action."""
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["resolve-blocker", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("dismiss the Safe Mode dialog", stdout)
        self.assertIn("Rejected for every other blocker type", stdout)
        self.assertIn("--hwnd", stdout)
        self.assertIn("--button", stdout)

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

    def test_ensure_closed_not_stopped_maps_to_exit_code_16(self):
        with mock.patch.object(unity_session, "ensure_closed", return_value=(False, _make_session())):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["ensure-closed", "--inspect-only"])

        self.assertEqual(exit_code, unity_puer_exec.EXIT_NOT_STOPPED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "not_stopped")
        self.assertNotIn("deprecated", payload)

    def test_ensure_stopped_alias_matches_ensure_closed_apart_from_deprecation(self):
        """The deprecated alias answers the same result with a `deprecated` field."""
        session = _make_session()
        with mock.patch.object(unity_session, "ensure_closed", return_value=(True, session)):
            canonical_code, canonical_out, _ = unity_puer_exec.run_cli(["ensure-closed", "--inspect-only"])
        with mock.patch.object(unity_session, "ensure_closed", return_value=(True, session)):
            alias_code, alias_out, _ = unity_puer_exec.run_cli(["ensure-stopped", "--inspect-only"])

        self.assertEqual(canonical_code, alias_code)
        alias_payload = json.loads(alias_out)
        canonical_payload = json.loads(canonical_out)
        deprecation = alias_payload.pop("deprecated")
        self.assertEqual(deprecation, {"alias": "ensure-stopped", "use": "ensure-closed"})
        self.assertEqual(alias_payload, canonical_payload)

    def test_ensure_closed_description_distinct_from_play_mode_stop(self):
        import help_surface

        top_level = help_surface.render_top_level_help()
        self.assertIn("ensure-closed", top_level)
        self.assertIn("close the Editor process", top_level)
        self.assertNotIn("ensure-stopped: ", top_level)
        alias_help = help_surface.render_command_help("ensure-stopped")
        self.assertIn("Deprecated alias of `ensure-closed`", alias_help)
        for flag in ("--help", "--help-args", "--help-status"):
            for command in ("ensure-closed", "ensure-stopped"):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([command, flag])
                self.assertEqual(exit_code, 0, (command, flag))
                self.assertTrue(stdout.strip(), (command, flag))

    def test_address_conflict_is_usage_error(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--project-path", "X:/a", "--base-url", "http://127.0.0.1:55231", "--code", "export default function run(ctx) { return 1; }"]
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "address_conflict")
        self.assertIn("situation", payload)
        self.assertIn("next_steps", payload)
        for step in payload["next_steps"]:
            argv = step.get("argv") or []
            self.assertFalse(
                "--project-path" in argv and "--base-url" in argv,
                "usage guidance must not re-offer the rejected dual-selector invocation",
            )

    def test_parse_unrecognized_option_emits_invalid_arguments_json(self):
        with mock.patch.object(unity_puer_exec.direct_exec_client, "invoke_command") as invoke:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["exec", "--timeout-ms", "5000", "--code", "export default function run(ctx) { return 1; }"]
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertNotIn("usage:", stderr.lower().split("{", 1)[0])
        body = json.loads(stderr)
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertNotEqual(body["status"], "failed")
        self.assertIn("error", body)
        self.assertEqual(body["command"], "exec")
        self.assertEqual(body["suggested_option"], "--wait-timeout-ms")
        self.assertIn("situation", body)
        self.assertIn("next_steps", body)
        help_step = body["next_steps"][0]
        self.assertEqual(help_step["argv"], ["unity-puer-exec", "exec", "--help-args"])
        # Top-level command list alone is not the response content.
        self.assertNotIn("Command Groups", stderr)
        invoke.assert_not_called()

    def test_parse_missing_required_argument_emits_invalid_arguments_json(self):
        with mock.patch.object(unity_session, "create_observation_session") as create_session:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertEqual(body["command"], "wait-for-exec")
        self.assertIn("request-id", body["error"])
        self.assertIn("next_steps", body)
        create_session.assert_not_called()

    def test_parse_invalid_value_emits_invalid_arguments_json(self):
        with mock.patch.object(unity_puer_exec.direct_exec_client, "invoke_command") as invoke:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "exec",
                    "--code", "export default function run(ctx) { return 1; }",
                    "--stale-module-policy", "invalid",
                ]
            )

        self.assertEqual(exit_code, 2)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertEqual(body["command"], "exec")
        self.assertIn("invalid", body["error"].lower())
        invoke.assert_not_called()

    def test_parse_failure_without_command_uses_top_level_guidance(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--not-a-real-flag"])

        self.assertEqual(exit_code, 2)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertNotIn("command", body)
        self.assertIn("top-level", body["situation"].lower())
        self.assertEqual(body["next_steps"][0]["argv"], ["unity-puer-exec", "--help"])

    def test_parse_near_match_omitted_when_no_close_option(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--definitely-not-a-flag", "--code", "export default function run(ctx) { return 1; }"]
        )

        self.assertEqual(exit_code, 2)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertNotIn("suggested_option", body)

    def test_parse_near_match_does_not_offer_other_command_options(self):
        # --timeout-seconds belongs to wait commands, not exec.
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--timeout-seconds", "5", "--code", "export default function run(ctx) { return 1; }"]
        )

        self.assertEqual(exit_code, 2)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "invalid_arguments")
        self.assertEqual(body["command"], "exec")
        # Even if a suggestion appears, it must be an exec option, never wait-only --timeout-seconds.
        if "suggested_option" in body:
            self.assertNotEqual(body["suggested_option"], "--timeout-seconds")
            parser = unity_puer_exec._build_parser()
            import unity_puer_exec_surface as surface

            self.assertIn(
                body["suggested_option"],
                surface.option_strings_for_command(parser, "exec"),
            )

    def test_usage_failure_guidance_does_not_offer_retry_of_rejected_invocation(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["get-log-briefs", "--range", "0-10", "--full-text"]
        )

        self.assertEqual(exit_code, 2)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "full_text_requires_include")
        self.assertIn("situation", body)
        self.assertIn("next_steps", body)
        for step in body["next_steps"]:
            argv = step.get("argv") or []
            self.assertNotIn("--full-text", argv)

    def test_help_status_documents_invalid_arguments_cli_wide(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("`invalid_arguments` -> exit 2", stdout)
        self.assertIn("CLI-wide usage status", stdout)

    def test_exec_removed_include_log_offset_usage_error_includes_situation(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(
            ["exec", "--project-path", "X:/a", "--include-log-offset", "--code", "export default function run(ctx) { return 1; }"]
        )

        self.assertEqual(exit_code, 2)
        payload = json.loads(stderr)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("situation", payload)

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
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["exec", "--project-path", "X:/project", "--code", "export default function run(ctx) { return 1; }"]
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_START_FAILED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_start_failed")
        self.assertEqual(payload["session"]["unity_pid"], 1234)

    def test_launch_conflict_maps_to_exit_code_20(self):
        session = _make_session()
        error = unity_session.UnityLaunchConflictError("launch ownership conflict", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["exec", "--project-path", "X:/project", "--code", "export default function run(ctx) { return 1; }"]
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_START_FAILED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "launch_conflict")
        self.assertEqual(payload["session"]["unity_pid"], 1234)

    def test_not_ready_during_exec_becomes_running_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            session = _make_session(project_path=str(project_path))
            error = unity_session.UnityNotReadyError("not ready", session=session)

            with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--code", "export default function run(ctx) { return 1; }"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
            self.assertEqual(stderr, "")
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "running")
            self.assertEqual(payload["operation"], "exec")
            self.assertIn("request_id", payload)


    def test_wait_for_exec_brief_sequence_grows_with_log(self):
        """Compact brief_sequence stays faithful as observed log activity accumulates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            # Blank lines separate runtime entries (the boundary the parser keys on);
            # without them consecutive non-indented lines are one merged brief.
            log_path.write_text(
                "Loading module assembly\n\nInitializing engine\n\nCompiling scripts\n",
                encoding="utf-8",
            )

            def _make_running_response(req_id):
                return (
                    unity_puer_exec.EXIT_RUNNING,
                    json.dumps({"ok": True, "status": "running", "request_id": req_id}),
                    "",
                )

            with mock.patch.object(
                unity_session_logs,
                "default_editor_log_path",
                return_value=log_path,
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=_make_running_response("req-grow"),
            ):
                # First call: observe brief_sequence at initial log size
                exit_code_1, stdout_1, _ = unity_puer_exec.run_cli([
                    "wait-for-exec", "--base-url", "http://127.0.0.1:55231",
                    "--request-id", "req-grow", "--log-start-offset", "0",
                ])
                body_1 = json.loads(stdout_1)
                seq_1 = body_1["brief_sequence"]
                log_range_1 = body_1["log_range"]

                # Append more log content
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        "\nRefreshing assets\n\n[Warning] Shader compilation slow\n\n"
                        "[Error] NullReferenceException\n  at Foo.Bar()\n"
                    )

                # Second call: same log_start_offset, log has grown
                exit_code_2, stdout_2, _ = unity_puer_exec.run_cli([
                    "wait-for-exec", "--base-url", "http://127.0.0.1:55231",
                    "--request-id", "req-grow", "--log-start-offset", "0",
                ])
                body_2 = json.loads(stdout_2)
                seq_2 = body_2["brief_sequence"]
                log_range_2 = body_2["log_range"]

            # Verify: log_range.start stays constant
            self.assertEqual(log_range_1["start"], 0)
            self.assertEqual(log_range_2["start"], 0)
            # Verify: log_range.end grew
            self.assertGreater(log_range_2["end"], log_range_1["end"])
            # Verify: compact encoding remains faithful even when extending a
            # repeated run changes the encoded prefix text.
            self.assertEqual(seq_1, "I3")
            self.assertEqual(seq_2, "I4WE")
            self.assertEqual(_expand_brief_sequence(seq_1), "III")
            self.assertEqual(_expand_brief_sequence(seq_2), "IIIIWE")
            self.assertTrue(
                _expand_brief_sequence(seq_2).startswith(_expand_brief_sequence(seq_1)),
                f"expanded seq_2={_expand_brief_sequence(seq_2)!r} should start with expanded seq_1={_expand_brief_sequence(seq_1)!r}",
            )


    def test_wait_for_log_pattern_success_includes_log_range(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("Loading module\n[Build] complete\n", encoding="utf-8")
            session = _make_session()
            session.diagnostics["matched_log_text"] = "[Build] complete"

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", return_value=session
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-log-pattern", "--pattern", r"\[Build\] complete", "--timeout-seconds", "5"]
                )

            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertIn("log_range", body)
            self.assertIn("start", body["log_range"])
            self.assertIn("end", body["log_range"])
            self.assertIn("brief_sequence", body)

    def test_wait_for_log_pattern_stall_includes_log_range(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("Loading module\n", encoding="utf-8")
            session = _make_session()
            stalled = unity_session.UnityStalledError("compiling", session=session)

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", side_effect=stalled
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-log-pattern", "--pattern", r"\[Build\] complete", "--timeout-seconds", "5"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_NOT_READY)
            body = json.loads(stdout)
            self.assertEqual(body["status"], "unity_stalled")
            self.assertEqual(body["operation"], "wait-for-log-pattern")
            self.assertIn("log_range", body)
            self.assertIn("brief_sequence", body)

    def test_wait_for_log_pattern_start_offset_sets_log_range_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("Loading module\n[Build] complete\n", encoding="utf-8")
            session = _make_session()

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", return_value=session
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-log-pattern", "--pattern", r"\[Build\]", "--start-offset", "5"]
                )

            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertEqual(body["log_range"]["start"], 5)

    def test_wait_for_result_marker_success_includes_log_range(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("Loading module\n", encoding="utf-8")
            session = _make_session()
            session.diagnostics["extracted_group"] = json.dumps({"correlation_id": "wanted"})
            session.diagnostics["matched_log_offset"] = 100

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", return_value=session
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-result-marker", "--correlation-id", "wanted"]
                )

            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertIn("log_range", body)
            self.assertIn("brief_sequence", body)

    def test_wait_for_result_marker_stall_includes_log_range(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("Loading module\n", encoding="utf-8")
            session = _make_session()
            stalled = unity_session.UnityStalledError("compiling", session=session)

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", side_effect=stalled
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["wait-for-result-marker", "--correlation-id", "wanted"]
                )

            self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_NOT_READY)
            body = json.loads(stdout)
            self.assertEqual(body["status"], "unity_stalled")
            self.assertEqual(body["operation"], "wait-for-result-marker")
            self.assertIn("log_range", body)
            self.assertIn("brief_sequence", body)

    def test_get_compile_errors_rejects_negative_start(self):
        """get-compile-errors rejects negative --start values."""
        # argparse accepts -1 as a valid integer; the runtime handler validates it
        args = unity_puer_exec._build_parser().parse_args([
            "get-compile-errors",
            "--project-path", "X:/proj",
            "--start", "-1",
        ])
        self.assertEqual(args.start, -1)
        # Runtime validation rejects negative start
        with self.assertRaises(ValueError):
            unity_puer_exec_runtime.run_get_compile_errors(args)

    def test_get_compile_errors_rejects_out_of_range_count(self):
        """get-compile-errors rejects --count values outside [1, 100]."""
        # argparse accepts 0 and 101 as valid integers; the runtime handler validates
        args = unity_puer_exec._build_parser().parse_args([
            "get-compile-errors",
            "--project-path", "X:/proj",
            "--count", "0",
        ])
        self.assertEqual(args.count, 0)
        # Runtime validation must reject count < 1 before any network call
        with self.assertRaises(ValueError):
            unity_puer_exec_runtime.run_get_compile_errors(args)
        args = unity_puer_exec._build_parser().parse_args([
            "get-compile-errors",
            "--project-path", "X:/proj",
            "--count", "101",
        ])
        self.assertEqual(args.count, 101)
        with self.assertRaises(ValueError):
            unity_puer_exec_runtime.run_get_compile_errors(args)

    def test_get_compile_warnings_accepts_valid_args(self):
        """get-compile-warnings accepts valid range arguments."""
        args = unity_puer_exec._build_parser().parse_args([
            "get-compile-warnings",
            "--project-path", "X:/proj",
            "--start", "5",
            "--count", "10",
        ])
        self.assertEqual(args.command, "get-compile-warnings")
        self.assertEqual(args.start, 5)
        self.assertEqual(args.count, 10)

    def test_get_compile_errors_in_command_tree(self):
        """get-compile-errors and get-compile-warnings are in the command tree."""
        parser = unity_puer_exec._build_parser()
        args = parser.parse_args(["get-compile-errors", "--project-path", "X:/proj"])
        self.assertEqual(args.command, "get-compile-errors")
        self.assertEqual(args.start, 0)
        self.assertEqual(args.count, 3)

        args = parser.parse_args(["get-compile-warnings", "--base-url", "http://127.0.0.1:55231"])
        self.assertEqual(args.command, "get-compile-warnings")

    # --- _extract_compile_errors_from_log ---

    def test_extract_compile_errors_standard_csharp_error(self):
        import tempfile, os
        content = "Assets/Scripts/Foo.cs(10,5): error CS1003: Syntax error, ',' expected\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = unity_puer_exec_runtime._extract_compile_errors_from_log(f.name)
        os.unlink(f.name)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_errors"], 1)
        self.assertEqual(result["errors"][0]["file"], "Assets/Scripts/Foo.cs")
        self.assertEqual(result["errors"][0]["line"], 10)
        self.assertEqual(result["errors"][0]["column"], 5)
        self.assertEqual(result["errors"][0]["code"], "CS1003")
        self.assertIn("Syntax error", result["errors"][0]["message"])

    def test_extract_compile_errors_uncoded_error(self):
        import tempfile, os
        content = "Packages/com.x/Editor/Foo.cs(3,1): error : Some message\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = unity_puer_exec_runtime._extract_compile_errors_from_log(f.name)
        os.unlink(f.name)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_errors"], 1)
        self.assertEqual(result["errors"][0]["file"], "Packages/com.x/Editor/Foo.cs")
        self.assertEqual(result["errors"][0]["code"], None)
        self.assertEqual(result["errors"][0]["message"], "Some message")

    def test_extract_compile_errors_windows_absolute_path(self):
        import tempfile, os
        content = "C:\\Project\\Assets\\Foo.cs(10,5): error CS1003: Syntax error\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = unity_puer_exec_runtime._extract_compile_errors_from_log(f.name)
        os.unlink(f.name)
        self.assertIsNotNone(result)
        self.assertIn("C:", result["errors"][0]["file"])
        self.assertTrue(result["errors"][0]["file"].endswith("Foo.cs"))

    def test_extract_compile_errors_multiline(self):
        import tempfile, os
        content = (
            "Assets/Foo.cs(5,1): error CS1234: First line\n"
            "  Second line continuation\n"
            "  Third line continuation\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = unity_puer_exec_runtime._extract_compile_errors_from_log(f.name)
        os.unlink(f.name)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_errors"], 1)
        self.assertIn("Second line continuation", result["errors"][0]["message"])
        self.assertIn("Third line continuation", result["errors"][0]["message"])

    def test_extract_compile_errors_no_errors(self):
        import tempfile, os
        content = "Some random log line\nAnother line with warning CS1234: blah\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = unity_puer_exec_runtime._extract_compile_errors_from_log(f.name)
        os.unlink(f.name)
        self.assertIsNone(result)

    def test_extract_compile_errors_nonexistent_file(self):
        result = unity_puer_exec_runtime._extract_compile_errors_from_log("/nonexistent/path.log")
        self.assertIsNone(result)

    def test_extract_compile_errors_none_path(self):
        result = unity_puer_exec_runtime._extract_compile_errors_from_log(None)
        self.assertIsNone(result)

    def test_exec_help_status_includes_unity_compile_error(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("unity_compile_error", stdout)
        self.assertIn("23", stdout)

    def test_guidance_matrix_has_unity_compile_error_for_exec(self):
        import help_surface
        entry = help_surface.GUIDANCE_MATRIX.get(("exec", "unity_compile_error"))
        self.assertIsNotNone(entry, "GUIDANCE_MATRIX missing (exec, unity_compile_error)")
        self.assertIn("situation", entry)
        self.assertIn("next_steps", entry)
        # The re-run guidance must not carry the removed refresh flag.
        next_steps = entry["next_steps"]
        exec_step = next((s for s in next_steps if s["command"] == "exec"), None)
        self.assertIsNotNone(exec_step, "next_steps missing exec candidate")
        self.assertIn("argv_template", exec_step)
        self.assertNotIn("--refresh-before-exec", exec_step["argv_template"])
        self.assertIn("saving the fix is itself enough", exec_step["when"])

    def test_guidance_matrix_has_unity_compile_error_for_wait_for_exec(self):
        import help_surface
        entry = help_surface.GUIDANCE_MATRIX.get(("wait-for-exec", "unity_compile_error"))
        self.assertIsNotNone(entry, "GUIDANCE_MATRIX missing (wait-for-exec, unity_compile_error)")
        self.assertIn("situation", entry)
        self.assertIn("next_steps", entry)

    def test_command_registry_tables_agree(self):
        """Argparse, help lists, top-level summaries, and guidance cover the same command set."""
        import command_registry
        import help_surface
        import unity_puer_exec_surface as surface

        parser = surface.build_parser()
        # Subparsers live on the action whose dest is "command".
        argparse_commands = set()
        for action in parser._actions:
            if getattr(action, "dest", None) == "command" and hasattr(action, "choices"):
                argparse_commands = set(action.choices or ())
                break

        registry = set(command_registry.INVOCABLE_COMMANDS)
        help_commands = set(help_surface.COMMANDS)
        command_help = set(help_surface.COMMAND_HELP)
        top_level = set(help_surface.TOP_LEVEL_COMMANDS)
        guidance = {command for command, _status in help_surface.GUIDANCE_MATRIX}

        # The invocable surface is the canonical tree plus derived aliases; the
        # help/guidance tables must cover exactly that surface.
        self.assertEqual(
            set(help_surface.INVOCABLE_COMMANDS),
            registry,
            "help_surface.INVOCABLE_COMMANDS must equal command_registry.INVOCABLE_COMMANDS",
        )
        for alias, canonical in command_registry.COMMAND_ALIASES:
            self.assertIn(canonical, command_registry.COMMANDS, alias)
            self.assertNotIn(alias, command_registry.COMMANDS, alias)

        tables = {
            "command_registry.INVOCABLE_COMMANDS": registry,
            "argparse subcommands": argparse_commands,
            "help_surface.COMMAND_HELP": command_help,
            "help_surface.TOP_LEVEL_COMMANDS": top_level,
            "help_surface.GUIDANCE_MATRIX": guidance,
        }
        mismatches = []
        for name, values in tables.items():
            missing = sorted(registry - values)
            extra = sorted(values - registry)
            if missing or extra:
                parts = []
                if missing:
                    parts.append("missing {}".format(", ".join(missing)))
                if extra:
                    parts.append("extra {}".format(", ".join(extra)))
                mismatches.append("{}: {}".format(name, "; ".join(parts)))
        self.assertEqual(mismatches, [], "command-table drift:\n" + "\n".join(mismatches))

    def test_formal_cli_contract_command_tree_matches_registry(self):
        """Durable formal-cli-contract command tree must match the code registry."""
        import re
        import command_registry

        spec_path = REPO_ROOT / "openspec" / "specs" / "formal-cli-contract" / "spec.md"
        text = spec_path.read_text(encoding="utf-8")
        match = re.search(
            r"authoritative flat command tree SHALL include ([^.]+)\.",
            text,
        )
        self.assertIsNotNone(match, "durable formal-cli-contract missing authoritative command tree sentence")
        named = set(re.findall(r"`([a-z0-9-]+)`", match.group(1)))
        registry = set(command_registry.COMMANDS)
        missing_from_spec = sorted(registry - named)
        extra_in_spec = sorted(named - registry)
        self.assertEqual(
            (missing_from_spec, extra_in_spec),
            ([], []),
            "formal-cli-contract tree drift: missing_from_spec={!r} extra_in_spec={!r}".format(
                missing_from_spec, extra_in_spec
            ),
        )

    def test_get_compile_errors_help_tiers_render(self):
        for flag in ("--help", "--help-args", "--help-status"):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-compile-errors", flag])
            self.assertEqual(exit_code, 0, flag)
            self.assertEqual(stderr, "", flag)
            self.assertTrue(stdout.strip(), flag)
        self.assertIn("--start", unity_puer_exec.run_cli(["get-compile-errors", "--help-args"])[1])
        self.assertIn("wait-for-compile", unity_puer_exec.run_cli(["get-compile-errors", "--help"])[1])

    def test_get_compile_warnings_help_tiers_render(self):
        for flag in ("--help", "--help-args", "--help-status"):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["get-compile-warnings", flag])
            self.assertEqual(exit_code, 0, flag)
            self.assertEqual(stderr, "", flag)
            self.assertTrue(stdout.strip(), flag)
        self.assertIn("--count", unity_puer_exec.run_cli(["get-compile-warnings", "--help-args"])[1])

    def test_top_level_help_lists_compile_message_commands(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--help"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("get-compile-errors", stdout)
        self.assertIn("get-compile-warnings", stdout)

    def test_get_compile_errors_non_success_carries_guidance(self):
        """A readiness failure attaches situation / next_steps for get-compile-errors."""
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            side_effect=unity_session.UnityNotReadyError("not ready", session=None),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["get-compile-errors", "--project-path", SAMPLE_PROJECT_PATH]
            )
        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_NOT_READY)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_not_ready")
        self.assertTrue(body.get("situation") or body.get("next_steps"))
        blob = json.dumps(body)
        self.assertIn("wait-for-compile", blob)

    def test_get_compile_warnings_non_success_carries_guidance(self):
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            side_effect=unity_session.UnityNotReadyError("not ready", session=None),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["get-compile-warnings", "--project-path", SAMPLE_PROJECT_PATH]
            )
        self.assertEqual(exit_code, unity_puer_exec.EXIT_UNITY_NOT_READY)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_not_ready")
        self.assertTrue(body.get("situation") or body.get("next_steps"))

    # --- Success-path guidance tests (fill-success-path-next-steps) ---

    def test_success_path_completed_guidance_matrix_entries_have_get_log_briefs(self):
        """3.1: exec/wait-for-exec/wait-for-log-pattern completed entries exist with get-log-briefs."""
        import help_surface
        for cmd in ("exec", "wait-for-exec", "wait-for-log-pattern"):
            entry = help_surface.GUIDANCE_MATRIX.get((cmd, "completed"))
            self.assertIsNotNone(entry, "GUIDANCE_MATRIX missing ({}, completed)".format(cmd))
            self.assertIn("next_steps", entry)
            next_steps = entry["next_steps"]
            brief_step = next((s for s in next_steps if s["command"] == "get-log-briefs"), None)
            self.assertIsNotNone(brief_step, "({}, completed) missing get-log-briefs candidate".format(cmd))
            self.assertIn("argv_template", brief_step)
            self.assertIn("{log_range_span}", str(brief_step["argv_template"]))
            self.assertIn("--levels", brief_step["argv_template"])
            self.assertIn("error,warning", brief_step["argv_template"])

    def test_wait_for_log_pattern_completed_has_situation_text(self):
        """3.2: wait-for-log-pattern completed situation warns about pattern match limits."""
        import help_surface
        entry = help_surface.GUIDANCE_MATRIX.get(("wait-for-log-pattern", "completed"))
        self.assertIsNotNone(entry)
        situation = entry.get("situation")
        self.assertIsNotNone(situation, "wait-for-log-pattern completed missing situation")
        self.assertIn("pattern match", situation.lower())
        # exec/wait-for-exec completed must NOT have a situation
        for cmd in ("exec", "wait-for-exec"):
            e2 = help_surface.GUIDANCE_MATRIX.get((cmd, "completed"))
            self.assertIsNotNone(e2)
            self.assertIsNone(e2.get("situation"), "({}, completed) should not have a situation".format(cmd))

    def test_completed_response_with_full_log_range_contains_get_log_briefs_argv(self):
        """3.1: Exec completed with full log_range and project-path produces argv with concrete range."""
        log_range_start = 1000
        log_range_end = 3500
        expected_span = "{}-{}".format(log_range_start, log_range_end)
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("line1\nline2\n", encoding="utf-8")
            session = _make_session()

            with mock.patch.object(
                unity_session, "ensure_session_ready", return_value=session
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client, "invoke_command",
                return_value=(
                    0,
                    json.dumps({
                        "ok": True, "status": "completed",
                        "request_id": "req-1",
                        "result": {"value": 42},
                    }),
                    "",
                ),
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ), mock.patch.object(
                unity_puer_exec_runtime, "_capture_log_offset",
                side_effect=[log_range_start, log_range_end],
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "exec", "--project-path", str(log_path.parent),
                    "--code", "export default function run(ctx) { return 42; }",
                ])

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        next_steps = body.get("next_steps")
        self.assertIsNotNone(next_steps, "exec completed missing next_steps")
        brief_step = next((s for s in next_steps if s["command"] == "get-log-briefs"), None)
        self.assertIsNotNone(brief_step, "next_steps missing get-log-briefs")
        self.assertIn("argv", brief_step)
        argv_str = " ".join(brief_step["argv"])
        self.assertIn("--range", argv_str)
        self.assertIn(expected_span, argv_str)
        self.assertIn("--levels", argv_str)
        self.assertIn("error,warning", argv_str)
        # exec completed should NOT have a situation
        self.assertNotIn("situation", body)

    def test_wait_for_log_pattern_completed_includes_situation_and_argv(self):
        """3.1+3.2: wait-for-log-pattern completed has both situation and get-log-briefs argv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("start\nmatch\n", encoding="utf-8")
            session = _make_session()
            session.diagnostics["matched_log_text"] = "match"

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", return_value=session
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "wait-for-log-pattern",
                    "--project-path", str(log_path.parent),
                    "--pattern", "match",
                    "--timeout-seconds", "5",
                    "--activity-timeout-seconds", "3",
                ])

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        # Should have situation text
        self.assertIn("situation", body)
        self.assertIn("pattern match", body["situation"].lower())
        # Should have next_steps with get-log-briefs
        next_steps = body.get("next_steps")
        self.assertIsNotNone(next_steps, "wait-for-log-pattern completed missing next_steps")
        brief_step = next((s for s in next_steps if s["command"] == "get-log-briefs"), None)
        self.assertIsNotNone(brief_step, "next_steps missing get-log-briefs")
        self.assertIn("argv", brief_step)

    def test_incomplete_log_range_omits_argv(self):
        """3.3: When log_range is incomplete, candidate appears without argv."""
        import help_surface
        # Verify the build_next_steps behavior with a context lacking log_range_span
        context = {"project_path": "X:/project"}
        next_steps = help_surface.build_next_steps("exec", "completed", context)
        self.assertIsNotNone(next_steps)
        brief_step = next((s for s in next_steps if s["command"] == "get-log-briefs"), None)
        self.assertIsNotNone(brief_step)
        # argv should be absent since log_range_span is missing
        self.assertNotIn("argv", brief_step)
        # command and when should still be present
        self.assertEqual(brief_step["command"], "get-log-briefs")
        self.assertIn("when", brief_step)

    def test_script_result_does_not_affect_candidates(self):
        """3.4: Script-authored result does not change success-path candidates."""
        import help_surface
        context = {
            "project_path": "X:/project",
            "log_range_span": "100-500",
        }
        # build_next_steps does not receive result at all, so identical context =
        # identical candidates regardless of what the envelope's result field says.
        next_steps_a = help_surface.build_next_steps("exec", "completed", context)
        next_steps_b = help_surface.build_next_steps("exec", "completed", context)
        self.assertEqual(next_steps_a, next_steps_b)

    def test_suppress_guidance_strips_success_path_content(self):
        """3.5: --suppress-guidance removes next_steps and situation on success paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text("line1\n", encoding="utf-8")
            session = _make_session()
            session.diagnostics["matched_log_text"] = "match"

            with mock.patch.object(
                unity_session, "create_observation_session", return_value=session
            ), mock.patch.object(
                unity_session, "wait_for_log_pattern", return_value=session
            ), mock.patch.object(
                unity_session_logs, "default_editor_log_path", return_value=log_path
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "--suppress-guidance",
                    "wait-for-log-pattern",
                    "--pattern", "match",
                    "--timeout-seconds", "5",
                    "--activity-timeout-seconds", "3",
                ])

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertNotIn("situation", body)
        self.assertNotIn("next_steps", body)


class DynamicEndpointRoutingTests(unittest.TestCase):
    """Project mode routes to non-default validated endpoint; direct base-url stays literal."""

    def test_project_mode_routes_to_validated_endpoint_non_default_port(self):
        """Project-scoped exec uses the base_url from ensure_session_ready, which may differ from 55231."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 1; }", encoding="utf-8")

            session = unity_session.UnitySession(
                owner="validated_artifact",
                base_url="http://127.0.0.1:55235",
                project_path=str(project_path),
                unity_pid=1234,
            )

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=session,
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed", "request_id": "req-1"}), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path)]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            # The invoke was to the session's base_url (non-default port), not the default
            self.assertEqual(invoke_command.call_args.args[1], "http://127.0.0.1:55235")

    def test_direct_base_url_mode_remains_literal(self):
        """Direct --base-url uses the provided URL literally, never rewrites from artifact."""
        with mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(0, json.dumps({"ok": True, "status": "completed", "request_id": "req-direct"}), ""),
        ) as invoke_command:
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["exec", "--base-url", "http://127.0.0.1:55999", "--code", "export default function run(ctx) { return 1; }"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(invoke_command.call_args.args[1], "http://127.0.0.1:55999")
        body = json.loads(stdout)
        self.assertNotIn("session", body)

    def test_direct_base_url_does_not_call_ensure_session_ready(self):
        """Direct --base-url bypasses project session readiness entirely."""
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
        ) as ensure_session_ready, mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(0, json.dumps({"ok": True, "status": "completed"}), ""),
        ):
            unity_puer_exec.run_cli(
                ["exec", "--base-url", "http://127.0.0.1:55999", "--code", "export default function run(ctx) { return 1; }"]
            )

        ensure_session_ready.assert_not_called()

    def test_project_mode_ensure_session_ready_defaults_to_standard_preferred_port(self):
        """When run_exec calls ensure_session_ready without base_url, it defaults to the preferred port."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 1; }", encoding="utf-8")

            session = unity_session.UnitySession(
                owner="existing_service",
                base_url="http://127.0.0.1:55231",
                project_path=str(project_path),
                unity_pid=1234,
            )

            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=session,
            ) as ensure_session_ready, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps({"ok": True, "status": "completed"}), ""),
            ):
                unity_puer_exec.run_cli(
                    ["exec", "--project-path", str(project_path), "--file", str(script_path)]
                )

            # ensure_session_ready uses the default base_url (preferred port) as fallback
            self.assertEqual(ensure_session_ready.call_count, 1)


class StackTraceDegradedBriefSequenceTests(unittest.TestCase):
    """When the host reports stack_trace_logging.degraded, the brief surface emits a
    sentinel + hint instead of a misleading brief_sequence."""

    def _write_log(self, content):
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def test_payload_degraded_emits_sentinel_and_hint(self):
        log_path = self._write_log("[UnityPuerExec] one\n[UnityPuerExec] two\n")
        payload = {
            "ok": True,
            "status": "completed",
            "stack_trace_logging": {
                "degraded": True,
                "log": "None",
                "warning": "ScriptOnly",
                "error": "ScriptOnly",
            },
        }
        unity_puer_exec_runtime._inject_log_range_into_payload(
            payload, log_path, 0, os.path.getsize(log_path)
        )
        self.assertEqual(
            payload["brief_sequence"],
            unity_puer_exec_runtime._BRIEF_SEQUENCE_STACKTRACE_OFF,
        )
        self.assertIn("brief_hint", payload)
        self.assertIn("stack trace logging", payload["brief_hint"].lower())
        self.assertEqual(payload["log_range"], {"start": 0, "end": os.path.getsize(log_path)})

    def test_payload_not_degraded_computes_normal_sequence(self):
        log_path = self._write_log("[UnityPuerExec] hello\n")
        payload = {
            "ok": True,
            "status": "completed",
            "stack_trace_logging": {
                "degraded": False,
                "log": "ScriptOnly",
                "warning": "ScriptOnly",
                "error": "ScriptOnly",
            },
        }
        unity_puer_exec_runtime._inject_log_range_into_payload(
            payload, log_path, 0, os.path.getsize(log_path)
        )
        self.assertNotEqual(
            payload["brief_sequence"],
            unity_puer_exec_runtime._BRIEF_SEQUENCE_STACKTRACE_OFF,
        )
        self.assertNotIn("brief_hint", payload)

    def test_missing_field_is_treated_as_not_degraded(self):
        # Backward compatibility: an older host with no stack_trace_logging field
        # must still produce a normal brief_sequence, never the sentinel.
        log_path = self._write_log("[UnityPuerExec] hello\n")
        payload = {"ok": True, "status": "completed"}
        unity_puer_exec_runtime._inject_log_range_into_payload(
            payload, log_path, 0, os.path.getsize(log_path)
        )
        self.assertNotEqual(
            payload["brief_sequence"],
            unity_puer_exec_runtime._BRIEF_SEQUENCE_STACKTRACE_OFF,
        )
        self.assertNotIn("brief_hint", payload)

    def test_stdout_injection_degraded_round_trips_sentinel(self):
        log_path = self._write_log("[UnityPuerExec] one\n[UnityPuerExec] two\n")
        stdout_text = json.dumps(
            {
                "ok": True,
                "status": "completed",
                "stack_trace_logging": {"degraded": True, "log": "None",
                                        "warning": "None", "error": "None"},
            }
        )
        result = unity_puer_exec_runtime._inject_log_range_into_stdout(
            stdout_text, log_path, 0, os.path.getsize(log_path)
        )
        body = json.loads(result)
        self.assertEqual(
            body["brief_sequence"],
            unity_puer_exec_runtime._BRIEF_SEQUENCE_STACKTRACE_OFF,
        )
        self.assertIn("brief_hint", body)


class _FakeClock:
    """Deterministic clock: time() advances only when sleep() is called."""

    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def _probe_from(statuses):
    """Build a probe_health_fn returning the given status sequence.

    Each entry is a health status string, or None to simulate a transport error.
    The final entry repeats once the sequence is exhausted.
    """
    seq = list(statuses)

    def probe(base_url, timeout_seconds):
        item = seq.pop(0) if len(seq) > 1 else seq[0]
        if item is None:
            return None, "connection refused"
        return {"ok": True, "status": item}, None

    return probe


def _probe_payloads(payloads):
    """Build a probe_health_fn returning full health payloads.

    The final payload repeats once the sequence is exhausted, so a single-element
    sequence models a steady state. A None entry simulates a transport error.
    """
    seq = list(payloads)

    def probe(base_url, timeout_seconds):
        item = seq.pop(0) if len(seq) > 1 else seq[0]
        if item is None:
            return None, "connection refused"
        return item, None

    return probe


def _play_mode_health(**refresh_overrides):
    refresh = {
        "pending": "pending",
        "suppressed": True,
        "suppressed_reason": "play_mode",
        "script_changes_while_playing": "recompile_after_finished_playing",
    }
    refresh.update(refresh_overrides)
    return {"ok": True, "status": "ready", "refresh": refresh}


class WaitForCompileCycleTests(unittest.TestCase):
    def _run(self, statuses, appear=10.0, settle=10.0):
        return unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            appear,
            settle,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_from(statuses),
            time_ref=_FakeClock(),
        )

    def test_compiling_appears_after_ready_then_settles(self):
        result = self._run(["ready", "ready", "compiling", "ready"])
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)
        self.assertIn("compiling", result["observed_health"])
        # An initial ready was never treated as terminal before the compile edge.
        self.assertEqual(result["observed_health"][-1], "ready")

    def test_compile_already_in_progress_settles(self):
        result = self._run(["compiling", "ready"])
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)
        self.assertEqual(result["observed_health"][0], "compiling")

    def test_no_compile_observed_within_appear_window(self):
        result = self._run(["ready"], appear=2.0)
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)

    def test_settle_timeout_when_compile_does_not_return_to_ready(self):
        result = self._run(["compiling"], settle=2.0)
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_TIMEOUT)

    def test_transient_transport_errors_tolerated_during_settle(self):
        result = self._run(["compiling", None, None, "ready"], settle=10.0)
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)

    def test_dropped_ready_endpoint_treated_as_compile_edge(self):
        # A previously-ready endpoint that drops (domain reload) is a compile edge.
        result = self._run(["ready", None, "ready"], appear=10.0)
        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)

    def test_consent_dialog_is_declined_while_health_stays_compiling(self):
        declined_pids = []

        def dismiss(pid):
            declined_pids.append(pid)
            return 1

        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            10.0,
            10.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_from(["compiling", "compiling", "ready"]),
            time_ref=_FakeClock(),
            unity_pid=4321,
            dismiss_fn=dismiss,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)
        # Once while the appear window observes compiling, once while settling.
        self.assertEqual(result["api_updater_declines"], 2)
        self.assertEqual(declined_pids, [4321, 4321])

    def test_consent_dialog_pid_falls_back_to_compiling_health(self):
        declined_pids = []

        def dismiss(pid):
            declined_pids.append(pid)
            return 1

        payloads = iter(
            [
                {"ok": False, "status": "compiling", "unity_pid": 9876},
                {"ok": True, "status": "ready"},
            ]
        )

        def probe(_base_url, _timeout):
            return next(payloads), None

        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            10.0,
            10.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=probe,
            time_ref=_FakeClock(),
            dismiss_fn=dismiss,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)
        self.assertEqual(declined_pids, [9876])

    def test_play_mode_pending_change_returns_compile_blocked_without_waiting(self):
        clock = _FakeClock()
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            30.0,
            30.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads([_play_mode_health()]),
            time_ref=clock,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_BLOCKED)
        self.assertEqual(result["reason"], "play_mode")
        self.assertEqual(
            result["script_changes_while_playing"], "recompile_after_finished_playing"
        )
        # The appear window was never entered: only one probe, no sleeping.
        self.assertEqual(clock.now, 0.0)
        self.assertEqual(result["observed_health"], ["ready"])

    def test_play_mode_with_nothing_pending_still_reports_no_compile_observed(self):
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            2.0,
            2.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads([
                _play_mode_health(pending="not_pending")
            ]),
            time_ref=_FakeClock(),
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)

    def test_play_mode_unknown_pending_is_not_treated_as_a_block(self):
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            2.0,
            2.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads([_play_mode_health(pending="unknown")]),
            time_ref=_FakeClock(),
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)

    def test_compile_already_in_progress_during_play_mode_still_settles(self):
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            10.0,
            10.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads([{"ok": False, "status": "compiling"}, {"ok": True, "status": "ready"}]),
            time_ref=_FakeClock(),
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_READY)

    def test_generation_baseline_advance_settles_an_inferred_compile(self):
        # The deferred play-exit compile crosses a domain reload that stops the
        # listener, so /health never serves `compiling`. The advanced baseline is the
        # only edge, and it must settle even though the first poll was already ready.
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            10.0,
            10.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads(
                [{"ok": True, "status": "ready", "compile_generation": 5}]
            ),
            time_ref=_FakeClock(),
            compile_generation_baseline=4,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_GENERATION)
        self.assertEqual(result["edge"], unity_puer_exec_runtime.COMPILE_EDGE_GENERATION_ADVANCE)
        self.assertEqual(result["compile_generation"], 5)
        self.assertEqual(result["observed_health"], ["ready"])

    def test_generation_baseline_equal_to_current_reports_no_compile(self):
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            2.0,
            2.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads(
                [{"ok": True, "status": "ready", "compile_generation": 5}]
            ),
            time_ref=_FakeClock(),
            compile_generation_baseline=5,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)

    def test_no_generation_baseline_after_reload_keeps_no_compile_observed(self):
        # A caller that starts after the reload without a baseline cannot be
        # retroactively satisfied, even when the reported generation is high.
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            2.0,
            2.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads(
                [{"ok": True, "status": "ready", "compile_generation": 5}]
            ),
            time_ref=_FakeClock(),
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)

    def test_baseline_with_absent_generation_field_keeps_existing_behavior(self):
        # An older Editor that predates the signal omits the field; a missing signal
        # must never fabricate an inferred compile.
        result = unity_puer_exec_runtime.wait_for_compile_cycle(
            "http://127.0.0.1:55231",
            2.0,
            2.0,
            unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
            probe_health_fn=_probe_payloads([{"ok": True, "status": "ready"}]),
            time_ref=_FakeClock(),
            compile_generation_baseline=4,
        )

        self.assertEqual(result["outcome"], unity_puer_exec_runtime.COMPILE_OUTCOME_NONE)


class WaitForCompileCommandTests(unittest.TestCase):
    def test_base_url_no_compile_observed_returns_distinct_outcome(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_from(["ready"]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231", "--appear-timeout-seconds", "2"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["operation"], "wait-for-compile")
        self.assertEqual(body["result"]["status"], "no_compile_observed")
        self.assertFalse(body["result"]["compile_observed"])

    def test_base_url_play_mode_block_returns_compile_blocked(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_payloads([_play_mode_health()]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231", "--appear-timeout-seconds", "2"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["status"], "compile_blocked")
        self.assertFalse(body["result"]["compile_observed"])
        self.assertEqual(body["result"]["reason"], "play_mode")
        self.assertEqual(
            body["result"]["script_changes_while_playing"],
            "recompile_after_finished_playing",
        )
        # Guidance leads out of play mode and never suggests forcing a compile.
        self.assertIn("play mode", body["situation"])
        self.assertIn("reload", body["situation"].lower())
        steps = body["next_steps"]
        self.assertTrue(any(step["command"] == "stop" for step in steps))
        self.assertNotIn("RequestScriptCompilation", json.dumps(steps))

    def test_base_url_play_mode_block_uses_unknown_preference_fallback(self):
        health = _play_mode_health()
        del health["refresh"]["script_changes_while_playing"]
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime, "_probe_compile_health", _probe_payloads([health])
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231"]
            )

        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "compile_blocked")
        self.assertEqual(body["result"]["script_changes_while_playing"], "unknown")

    def test_base_url_compile_settled_returns_completed(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_from(["compiling", "ready"]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231"]
            )

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "compile_settled")
        self.assertTrue(body["result"]["compile_observed"])

    def test_base_url_generation_baseline_settles_inferred_compile_and_names_the_edge(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_payloads([{"ok": True, "status": "ready", "compile_generation": 7}]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "wait-for-compile",
                    "--base-url", "http://127.0.0.1:55231",
                    "--compile-generation-baseline", "6",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["status"], "compile_settled")
        self.assertTrue(body["result"]["compile_observed"])
        self.assertEqual(body["result"]["edge"], "generation_advance")
        self.assertEqual(body["result"]["compile_generation"], 7)
        self.assertEqual(body["result"]["compile_generation_baseline"], 6)

    def test_base_url_generation_baseline_current_keeps_no_compile_observed(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_payloads([{"ok": True, "status": "ready", "compile_generation": 7}]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                [
                    "wait-for-compile",
                    "--base-url", "http://127.0.0.1:55231",
                    "--appear-timeout-seconds", "2",
                    "--compile-generation-baseline", "7",
                ]
            )

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "no_compile_observed")
        self.assertFalse(body["result"]["compile_observed"])
        self.assertNotIn("edge", body["result"])

    def test_base_url_without_generation_baseline_after_reload_keeps_no_compile_observed(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_payloads([{"ok": True, "status": "ready", "compile_generation": 7}]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231", "--appear-timeout-seconds", "2"]
            )

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "no_compile_observed")
        self.assertFalse(body["result"]["compile_observed"])

    def test_compile_generation_baseline_option_is_documented_in_help(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-compile", "--help-args"])

        self.assertEqual(exit_code, 0)
        self.assertIn("--compile-generation-baseline", stdout)

    def test_base_url_settle_timeout_returns_non_terminal_running(self):
        with mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_from(["compiling"]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--base-url", "http://127.0.0.1:55231", "--settle-timeout-seconds", "2"]
            )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["phase"], "compiling")

    def test_project_path_resolves_through_session_discovery(self):
        with mock.patch.object(
            unity_session,
            "ensure_session_ready",
            return_value=_make_session(),
        ) as ensure_ready, mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "_probe_compile_health",
            _probe_from(["compiling", "ready"]),
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--project-path", SAMPLE_PROJECT_PATH]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(ensure_ready.called)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "compile_settled")

    def test_help_documents_async_compile_and_trigger_tradeoff(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-compile", "--help"])
        self.assertEqual(exit_code, 0)
        self.assertIn("asynchronously", stdout)
        self.assertIn("RequestScriptCompilation", stdout)


class ApiUpdaterRecoveryCommandTests(unittest.TestCase):
    def test_wait_for_compile_decline_attaches_warning_to_compile_settled(self):
        session = _make_session()
        session.api_updater_declines = 1
        with mock.patch.object(
            unity_session, "ensure_session_ready", return_value=session
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={"outcome": "ready", "observed_health": ["compiling", "ready"], "api_updater_declines": 0},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--project-path", SAMPLE_PROJECT_PATH]
            )

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["status"], "compile_settled")
        self.assertEqual(body["warning"], "api_updater_declined")
        self.assertIn("warning_detail", body)

    def test_wait_for_compile_without_decline_omits_warning(self):
        with mock.patch.object(
            unity_session, "ensure_session_ready", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={"outcome": "ready", "observed_health": ["compiling", "ready"], "api_updater_declines": 0},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-compile", "--project-path", SAMPLE_PROJECT_PATH]
            )

        body = json.loads(stdout)
        self.assertNotIn("warning", body)

    def test_assembly_updater_log_line_alone_does_not_set_the_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Editor.log"
            log_path.write_text(
                "[Assembly Updater] warning: Ignoring assembly Library/ScriptAssemblies/Foo.dll\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                unity_session, "ensure_session_ready", return_value=_make_session()
            ), mock.patch.object(
                unity_puer_exec_runtime,
                "wait_for_compile_cycle",
                return_value={
                    "outcome": "ready",
                    "observed_health": ["compiling", "ready"],
                    "api_updater_declines": 0,
                },
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    [
                        "wait-for-compile",
                        "--project-path",
                        SAMPLE_PROJECT_PATH,
                        "--unity-log-path",
                        str(log_path),
                    ]
                )

        body = json.loads(stdout)
        self.assertNotIn("warning", body)

    def test_exec_timeout_auto_declines_consent_dialog_instead_of_modal_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session, "ensure_session_ready", return_value=_make_session()
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    unity_puer_exec.EXIT_NOT_AVAILABLE,
                    json.dumps(
                        {"ok": False, "status": "not_available", "request_id": "req-apu-timeout", "error": "timed out"}
                    ),
                    "",
                ),
            ), mock.patch.object(
                unity_puer_exec_runtime.unity_modal_blockers,
                "dismiss_api_updater_dialog",
                return_value={"ok": True, "status": "dismissed", "dismissed": 1},
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--file", str(script_path), "--request-id", "req-apu-timeout"]
                )

        body = json.loads(stdout)
        self.assertNotEqual(body.get("status"), "modal_blocked")
        self.assertEqual(body["warning"], "api_updater_declined")
        self.assertEqual(body["request_id"], "req-apu-timeout")

    def test_wait_for_exec_running_auto_declines_consent_dialog(self):
        with mock.patch.object(
            unity_session, "ensure_session_ready", return_value=_make_session()
        ), mock.patch.object(
            unity_puer_exec.direct_exec_client,
            "invoke_command",
            return_value=(
                unity_puer_exec.EXIT_RUNNING,
                json.dumps({"ok": True, "status": "running", "request_id": "req-apu-running"}),
                "",
            ),
        ), mock.patch.object(
            unity_puer_exec_runtime.unity_modal_blockers,
            "dismiss_api_updater_dialog",
            return_value={"ok": True, "status": "dismissed", "dismissed": 1},
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                ["wait-for-exec", "--request-id", "req-apu-running"]
            )

        body = json.loads(stdout)
        self.assertNotEqual(body.get("status"), "modal_blocked")
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["warning"], "api_updater_declined")

    def test_exec_compile_error_after_a_decline_still_carries_the_warning(self):
        session = _make_session()
        session.api_updater_declines = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            with mock.patch.object(
                unity_session, "ensure_session_ready", return_value=session
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(
                    unity_puer_exec.direct_exec_client.EXIT_UNITY_COMPILE_ERROR,
                    json.dumps(
                        {
                            "ok": False,
                            "status": "unity_compile_error",
                            "request_id": "req-apu-compile",
                            "compile_errors_total": 1,
                            "compile_messages": [],
                        }
                    ),
                    "",
                ),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--file", str(script_path), "--request-id", "req-apu-compile"]
                )

        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_compile_error")
        self.assertEqual(body["warning"], "api_updater_declined")

    def test_wait_for_compile_help_documents_auto_decline_and_warning(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-compile", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ScriptUpdater consent dialog", stdout)
        self.assertIn("api_updater_declined", stdout)

        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-compile", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("api_updater_declined", stdout)

    def test_exec_help_documents_auto_decline_and_warning(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ScriptUpdater consent dialog", stdout)
        self.assertIn("api_updater_declined", stdout)

        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("api_updater_declined", stdout)


class ExecPlayModeCompileBlockTests(unittest.TestCase):
    """Exec discloses a compile blocked by play mode (surface-play-mode-compile-block)."""

    SCRIPT = "export default function run(ctx) { return { value: 1 }; }"

    def _play_mode_refresh(self, paths):
        return {
            "triggered": False,
            "reason": "",
            "paths_changed": paths,
            "skipped_reason": "play_mode",
            "settle_outcome": "not_attempted",
            "elapsed_ms": 0,
        }

    def _completed_body(self, paths):
        return {
            "ok": True,
            "status": "completed",
            "operation": "exec",
            "request_id": "R-play",
            "result": {"value": 1},
            "refresh": self._play_mode_refresh(paths),
        }

    def _run_exec(self, invoke_return, health_preference=None):
        health = _play_mode_health()
        if health_preference is not None:
            health["refresh"]["script_changes_while_playing"] = health_preference
        with mock.patch.object(
            unity_puer_exec.direct_exec_client, "invoke_command", return_value=invoke_return
        ), mock.patch.object(
            unity_puer_exec_runtime, "time", _FakeClock()
        ), mock.patch.object(
            unity_puer_exec_runtime, "_probe_compile_health", _probe_payloads([health])
        ):
            return unity_puer_exec.run_cli(
                [
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", self.SCRIPT,
                    "--request-id", "R-play",
                ]
            )

    def test_completed_becomes_warning_with_compile_blocked(self):
        exit_code, stdout, stderr = self._run_exec(
            (0, json.dumps(self._completed_body(["C:/Project/Assets/A.cs"])), ""),
            health_preference="stop_playing_and_recompile",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "warning")
        self.assertEqual(body["warning"], "compile_blocked_by_play_mode")
        self.assertIn("warning_detail", body)
        # The script still ran and its return value survives.
        self.assertEqual(body["result"], {"value": 1})
        blocked = body["compile_blocked"]
        self.assertEqual(blocked["reason"], "play_mode")
        self.assertEqual(blocked["pending_paths"], ["C:/Project/Assets/A.cs"])
        self.assertEqual(blocked["script_changes_while_playing"], "stop_playing_and_recompile")
        # Guidance leads out of play mode and never picks the wrong remedy.
        self.assertIn("play mode", body["situation"])
        self.assertIn("reload", body["situation"].lower())
        self.assertTrue(any(step["command"] == "stop" for step in body["next_steps"]))
        self.assertNotIn("RequestScriptCompilation", json.dumps(body["next_steps"]))
        # The reload window is named so an unreachable endpoint is not read as a failure.
        self.assertIn("unreachable", json.dumps(body["next_steps"]))

    def test_nothing_pending_stays_completed_without_compile_blocked(self):
        exit_code, stdout, stderr = self._run_exec(
            (0, json.dumps(self._completed_body([])), "")
        )

        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertNotIn("compile_blocked", body)
        self.assertNotIn("warning", body)

    def test_script_failure_keeps_failure_status_and_still_carries_object(self):
        failure = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-play",
            "error": "TypeError: boom",
            "refresh": self._play_mode_refresh(["C:/Project/Assets/B.cs"]),
        }
        exit_code, stdout, stderr = self._run_exec((1, "", json.dumps(failure)))

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["compile_blocked"]["reason"], "play_mode")
        self.assertEqual(body["compile_blocked"]["pending_paths"], ["C:/Project/Assets/B.cs"])

    def test_async_warning_keeps_its_code_alongside_the_block(self):
        async_warning = {
            "ok": True,
            "status": "warning",
            "operation": "exec",
            "request_id": "R-play",
            "warning": "async_result_not_supported",
            "warning_detail": "The entry function returned a Promise.",
            "refresh": self._play_mode_refresh(["C:/Project/Assets/C.cs"]),
        }
        exit_code, stdout, stderr = self._run_exec((0, json.dumps(async_warning), ""))

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "warning")
        self.assertEqual(body["warning"], "async_result_not_supported")
        self.assertEqual(body["compile_blocked"]["reason"], "play_mode")
        # The single warning code is unchanged; no multi-warning shape is introduced.
        self.assertNotIn("warnings", body)
        # Guidance merges both conditions: the play-mode way out leads, and the
        # async follow-up is preserved rather than replaced.
        self.assertIn("play mode", body["situation"])
        self.assertIn("Promise", body["situation"])
        self.assertEqual(body["next_steps"][0]["command"], "stop")
        self.assertTrue(any(step["command"] == "wait-for-result-marker" for step in body["next_steps"]))

    def test_completed_without_play_mode_skip_is_untouched(self):
        completed = {
            "ok": True,
            "status": "completed",
            "operation": "exec",
            "request_id": "R-play",
            "result": {"value": 1},
            "refresh": {
                "triggered": False,
                "reason": "no_pending_change",
                "paths_changed": [],
                "skipped_reason": "",
                "settle_outcome": "not_attempted",
                "elapsed_ms": 0,
            },
        }
        exit_code, stdout, stderr = self._run_exec((0, json.dumps(completed), ""))

        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertNotIn("compile_blocked", body)

    def test_help_status_lists_compile_blocked_by_play_mode(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["exec", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("compile_blocked_by_play_mode", stdout)

        entry = help_surface.WARNING_GUIDANCE_MATRIX[("exec", "compile_blocked_by_play_mode")]
        self.assertIn("situation", entry)
        self.assertIn("play mode", entry["situation"])
        self.assertNotIn("RequestScriptCompilation", json.dumps(entry["next_steps"]))

    def test_wait_for_compile_help_status_lists_compile_blocked(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-compile", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("compile_blocked", stdout)

        entry = help_surface.GUIDANCE_MATRIX[("wait-for-compile", "compile_blocked")]
        self.assertIn("play mode", entry["situation"])
        self.assertNotIn("RequestScriptCompilation", json.dumps(entry["next_steps"]))
        self.assertNotIn("RequestScriptCompilation", entry["situation"])

    def test_no_compile_observed_guidance_warns_about_play_mode(self):
        entry = help_surface.GUIDANCE_MATRIX[("wait-for-compile", "no_compile_observed")]
        self.assertIn("play mode", entry["situation"])
        self.assertNotIn("RequestScriptCompilation", json.dumps(entry["next_steps"]))


class WaitForExecPlayModeCompileBlockTests(unittest.TestCase):
    """wait-for-exec discloses the same play-mode block as exec."""

    def _play_mode_refresh(self, paths):
        return {
            "triggered": False,
            "reason": "",
            "paths_changed": paths,
            "skipped_reason": "play_mode",
            "settle_outcome": "not_attempted",
            "elapsed_ms": 0,
        }

    def _run_replay(self, replayed, health_preference=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            project_path.mkdir()
            unity_session.write_pending_exec_artifact(
                str(project_path),
                "R-play",
                {
                    "request_id": "R-play",
                    "code": "export default function run(ctx) { return { value: 1 }; }",
                    "script_args": {},
                    "script_args_json": "{}",
                },
            )
            health = _play_mode_health()
            if health_preference is not None:
                health["refresh"]["script_changes_while_playing"] = health_preference
            with mock.patch.object(
                unity_session,
                "ensure_session_ready",
                return_value=_make_session(project_path=str(project_path)),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client, "invoke_command", return_value=replayed
            ), mock.patch.object(
                unity_puer_exec_runtime, "time", _FakeClock()
            ), mock.patch.object(
                unity_puer_exec_runtime, "_probe_compile_health", _probe_payloads([health])
            ):
                return unity_puer_exec.run_cli(
                    ["wait-for-exec", "--project-path", str(project_path), "--request-id", "R-play"]
                )

    def _completed_replay(self, paths):
        return (
            0,
            json.dumps(
                {
                    "ok": True,
                    "status": "completed",
                    "operation": "exec",
                    "request_id": "R-play",
                    "result": {"value": 1},
                    "refresh": self._play_mode_refresh(paths),
                }
            ),
            "",
        )

    def test_replay_discloses_play_mode_block_like_exec(self):
        exit_code, stdout, stderr = self._run_replay(
            self._completed_replay(["C:/Project/Assets/A.cs"]),
            health_preference="stop_playing_and_recompile",
        )

        self.assertEqual(exit_code, 0, stderr)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "warning")
        self.assertEqual(body["warning"], "compile_blocked_by_play_mode")
        self.assertIn("warning_detail", body)
        # The script still ran and its return value survives.
        self.assertEqual(body["result"], {"value": 1})
        self.assertEqual(body["compile_blocked"]["reason"], "play_mode")
        self.assertEqual(body["compile_blocked"]["pending_paths"], ["C:/Project/Assets/A.cs"])
        self.assertEqual(
            body["compile_blocked"]["script_changes_while_playing"], "stop_playing_and_recompile"
        )
        # No protocol change: the replay carries the server's refresh fields unchanged.
        self.assertEqual(body["refresh"]["skipped_reason"], "play_mode")
        self.assertEqual(body["refresh"]["paths_changed"], ["C:/Project/Assets/A.cs"])
        # Guidance leads out of play mode.
        self.assertIn("play mode", body["situation"])
        self.assertTrue(any(step["command"] == "stop" for step in body["next_steps"]))

    def test_replay_failure_keeps_status_and_carries_object(self):
        failure = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-play",
            "error": "TypeError: boom",
            "refresh": self._play_mode_refresh(["C:/Project/Assets/B.cs"]),
        }
        exit_code, stdout, stderr = self._run_replay((1, "", json.dumps(failure)))

        self.assertEqual(exit_code, 1)
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["compile_blocked"]["reason"], "play_mode")
        self.assertEqual(body["compile_blocked"]["pending_paths"], ["C:/Project/Assets/B.cs"])

    def test_replay_with_nothing_pending_is_not_rewritten(self):
        exit_code, stdout, stderr = self._run_replay(self._completed_replay([]))

        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertNotIn("compile_blocked", body)
        self.assertNotIn("warning", body)

    def test_non_terminal_replay_is_not_annotated(self):
        running = {
            "ok": True,
            "status": "running",
            "operation": "exec",
            "request_id": "R-play",
            "refresh": self._play_mode_refresh(["C:/Project/Assets/A.cs"]),
        }
        exit_code, stdout, stderr = self._run_replay(
            (unity_puer_exec.EXIT_RUNNING, json.dumps(running), "")
        )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertNotIn("compile_blocked", body)
        self.assertNotEqual(body.get("warning"), "compile_blocked_by_play_mode")
        self.assertNotIn("compile_blocked_by_play_mode", json.dumps(body.get("next_steps", [])))

    def test_wait_for_exec_help_status_lists_play_mode_warning(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["wait-for-exec", "--help-status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("compile_blocked_by_play_mode", stdout)

        entry = help_surface.WARNING_GUIDANCE_MATRIX[
            ("wait-for-exec", "compile_blocked_by_play_mode")
        ]
        self.assertIn("play mode", entry["situation"])
        self.assertNotIn("RequestScriptCompilation", json.dumps(entry["next_steps"]))


class ScriptChangesWhilePlayingParsingTests(unittest.TestCase):
    """Python-side read of the server's Script Changes While Playing preference."""

    def test_known_labels_are_passed_through(self):
        for label in (
            "recompile_and_continue_playing",
            "recompile_after_finished_playing",
            "stop_playing_and_recompile",
        ):
            payload = {"refresh": {"script_changes_while_playing": label}}
            self.assertEqual(
                unity_puer_exec_runtime._script_changes_while_playing_from_health(payload),
                label,
            )

    def test_missing_field_or_payload_falls_back_to_unknown(self):
        self.assertEqual(
            unity_puer_exec_runtime._script_changes_while_playing_from_health({"refresh": {}}),
            "unknown",
        )
        self.assertEqual(
            unity_puer_exec_runtime._script_changes_while_playing_from_health({}),
            "unknown",
        )
        self.assertEqual(
            unity_puer_exec_runtime._script_changes_while_playing_from_health(None),
            "unknown",
        )


class _CompileCycleClock:
    """Deterministic stand-in for wall time across a refresh-triggered compile.

    `wait_for_compile_cycle` sleeps in real seconds; a compile plus the domain
    reload it ends with cannot be produced in a unit test, so the cycle is modelled
    as a clock the probe reads. Advancing only on `sleep` keeps the settle loop's
    own budget arithmetic intact -- which is the thing under test.
    """

    def __init__(self, ready_after_seconds):
        self.now = 0.0
        self.ready_after_seconds = ready_after_seconds

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class _FakeSession:
    """Minimal session stand-in for project-path guidance assertions."""

    def __init__(self, base_url="http://127.0.0.1:55231"):
        self.base_url = base_url
        self.api_updater_declines = 0
        self.unity_pid = 4242

    def to_payload(self):
        return {"base_url": self.base_url}


class AutomaticRefreshBaseUrlTests(unittest.TestCase):
    def test_base_url_automatic_refresh_settles_cycle_longer_than_wait_timeout(self):
        """A base-url refresh must settle the compile+reload it triggered.

        Regression for the deterministic real-host failure of
        `test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`: the
        automatic-refresh settle budget was derived from `--wait-timeout-ms`, which
        bounds one HTTP wait for an already-accepted job, not a compile cycle. With
        the test's 1000 ms budget no compile+domain-reload can settle, so `exec`
        returned `running`/`refreshing` without resubmitting -- and in base-url mode
        there is no pending artifact to replay, while the server never accepted the
        job, so the promised `wait-for-exec --request-id` continuation answers
        `missing` with no script result.

        The cycle here takes longer than the caller's `--wait-timeout-ms` but far
        inside a compile-scale budget, so a correct CLI settles, resubmits under the
        same request_id, and returns the script result.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-base",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": ["C:/Project/Assets/A.cs"],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            clock = _CompileCycleClock(ready_after_seconds=3.0)

            def probe(base_url, timeout_seconds):
                status = "compiling" if clock.now < clock.ready_after_seconds else "ready"
                return {"ok": True, "status": status, "session_marker": "m1"}, None

            with mock.patch.object(unity_puer_exec_runtime, "time", clock), mock.patch.object(
                unity_puer_exec_runtime, "_probe_compile_health", side_effect=probe
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-base", "result": {"value": 7}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    [
                        "exec",
                        "--base-url", "http://127.0.0.1:55231",
                        "--wait-timeout-ms", "1000",
                        "--file", str(script_path),
                        "--request-id", "req-base",
                    ]
                )

        self.assertEqual(stderr, "")
        # The settle must outlive the caller's per-request wait budget, then resubmit
        # under the same request_id.
        self.assertEqual(invoke_command.call_count, 2)
        self.assertEqual(exit_code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"], {"value": 7})
        self.assertTrue(body["refresh"]["triggered"])

    def test_base_url_automatic_refresh_runs_user_script_after_settle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-base",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": ["C:/Project/Assets/A.cs"],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            with mock.patch.object(
                unity_puer_exec_runtime,
                "_settle_base_url_after_refresh",
                return_value={"outcome": "ready", "observed_health": ["compiling", "ready"]},
            ) as settle, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
                    (0, json.dumps({"ok": True, "status": "completed", "request_id": "req-base", "result": {"value": 7}}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--base-url", "http://127.0.0.1:55231", "--file", str(script_path), "--request-id", "req-base"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(settle.called)
        self.assertEqual(invoke_command.call_count, 2)
        self.assertNotIn("refresh_before_exec", invoke_command.call_args_list[0].args[2])
        self.assertEqual(invoke_command.call_args_list[0].args[2]["request_id"], "req-base")
        self.assertEqual(invoke_command.call_args_list[1].args[2]["request_id"], "req-base")
        self.assertIn("return 7", invoke_command.call_args_list[1].args[2]["code"])
        body = json.loads(stdout)
        # Terminal response carries the script result, not {refreshed: true}.
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["value"], 7)
        self.assertTrue(body["refresh"]["triggered"])

    def test_base_url_automatic_refresh_settle_timeout_reports_refresh_unsettled(self):
        """An unsettleable base-url refresh must not promise a `missing` continuation.

        The settle budget is compile-scale, so a refresh that is still compiling when
        it expires is not going to converge in this invocation. Reporting `running`
        here attached the ("exec", "running") guidance, whose first candidate is
        `wait-for-exec --request-id` -- but base-url mode writes no pending artifact
        and the server answers `TryAcceptExecRequest` only after the refreshing phase,
        so that continuation always answered non-recoverable `missing`.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-base",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": [],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            with mock.patch.object(
                unity_puer_exec_runtime,
                "_settle_base_url_after_refresh",
                return_value={"outcome": "settle_timeout", "observed_health": ["compiling"]},
            ) as settle, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--base-url", "http://127.0.0.1:55231", "--file", str(script_path), "--request-id", "req-base"]
                )

        self.assertEqual(stderr, "")
        self.assertTrue(settle.called)
        # A settle that did not return to ready still gets no second submit.
        self.assertEqual(invoke_command.call_count, 1)
        self.assertEqual(exit_code, unity_puer_exec.EXIT_REFRESH_UNSETTLED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "refresh_unsettled")
        self.assertEqual(body["request_id"], "req-base")
        self.assertEqual(body["reason"], "refresh_settle_timeout")
        self.assertTrue(body["refresh"]["triggered"])
        # The reply is explicitly NOT a lost record, and it is resubmit-safe.
        self.assertFalse(body["record_replayable"])
        self.assertTrue(body["resubmit_safe"])
        self.assertNotEqual(exit_code, unity_puer_exec.EXIT_MISSING)
        # No continuation the caller cannot actually take.
        commands = [step["command"] for step in body.get("next_steps", [])]
        self.assertNotIn("wait-for-exec", commands)
        self.assertIn("exec", commands)
        resubmit = next(step for step in body["next_steps"] if step["command"] == "exec")
        self.assertEqual(
            resubmit["argv"],
            ["unity-puer-exec", "exec", "--base-url", "http://127.0.0.1:55231", "--request-id", "req-base"],
        )

    def test_base_url_automatic_refresh_persisting_after_resubmit_is_refresh_unsettled(self):
        """A second `refreshing` after the one permitted resubmit is also terminal.

        The server keeps reporting a compile-triggering change, so the request is
        still unaccepted and base-url mode still keeps no record. This is the second
        branch whose advertised continuation could not work.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-base",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": ["C:/Project/Assets/A.cs"],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            with mock.patch.object(
                unity_puer_exec_runtime,
                "_settle_base_url_after_refresh",
                return_value={"outcome": "ready", "observed_health": ["compiling", "ready"]},
            ) as settle, mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--base-url", "http://127.0.0.1:55231", "--file", str(script_path), "--request-id", "req-base"]
                )

        self.assertEqual(stderr, "")
        self.assertTrue(settle.called)
        # One submit, one resubmit, then the exhaustion report.
        self.assertEqual(invoke_command.call_count, 2)
        self.assertEqual(exit_code, unity_puer_exec.EXIT_REFRESH_UNSETTLED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "refresh_unsettled")
        self.assertEqual(body["reason"], "refresh_persisted")
        self.assertNotIn("wait-for-exec", [step["command"] for step in body.get("next_steps", [])])

    def test_base_url_resubmit_answered_compiling_is_refresh_unsettled(self):
        """A post-settle resubmit answered `compiling` has no record to continue.

        The server rejects `/exec` with `{"ok":false,"status":"compiling"}` before
        `TryAcceptExecRequest`, so no job exists. Project-path mode normalizes this
        to `running` because its pending artifact can be replayed; base-url mode has
        none, so the response must not look like an accepted request.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-base",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": [],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            with mock.patch.object(
                unity_puer_exec_runtime,
                "_settle_base_url_after_refresh",
                return_value={"outcome": "ready", "observed_health": ["compiling", "ready"]},
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                side_effect=[
                    (unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
                    (unity_puer_exec.EXIT_COMPILING, json.dumps({"ok": False, "status": "compiling"}), ""),
                ],
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--base-url", "http://127.0.0.1:55231", "--file", str(script_path), "--request-id", "req-base"]
                )

        self.assertEqual(stderr, "")
        self.assertEqual(invoke_command.call_count, 2)
        self.assertEqual(exit_code, unity_puer_exec.EXIT_REFRESH_UNSETTLED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "refresh_unsettled")
        self.assertEqual(body["reason"], "compile_in_progress")
        self.assertEqual(body["phase"], "compiling")
        self.assertNotIn("wait-for-exec", [step["command"] for step in body.get("next_steps", [])])

    def test_base_url_running_does_not_advertise_unreachable_wait_for_exec(self):
        """`exec --base-url` returning `running` still promises an accepted request.

        A base-url accepted request does have a server-side job, so
        `wait-for-exec --base-url --request-id` would work -- but the candidate
        template needs a `--project-path` that base-url mode does not have. The
        unreachable-continuation rule is about reachability, so nothing is advertised.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            running_body = {
                "ok": True,
                "status": "running",
                "request_id": "req-base",
            }
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps(running_body), ""),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    ["exec", "--base-url", "http://127.0.0.1:55231", "--file", str(script_path), "--request-id", "req-base"]
                )

        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        commands = [step["command"] for step in body.get("next_steps", [])]
        self.assertNotIn("wait-for-exec", commands)
        # The other, genuinely usable candidates survive.
        self.assertIn("wait-for-result-marker", commands)

    def test_project_path_refresh_still_reports_running_with_replayable_guidance(self):
        """The project-path branch keeps its `running` shape and its continuation.

        Guard against a fix that silences the replayable case: here the pending
        artifact exists, so `wait-for-exec --project-path --request-id` really can
        continue the request and must still be advertised.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "Project"
            (project / "Assets").mkdir(parents=True)
            script_path = Path(temp_dir) / "script.js"
            script_path.write_text("export default function run(ctx) { return 7; }", encoding="utf-8")
            refresh_body = {
                "ok": True,
                "status": "running",
                "phase": "refreshing",
                "request_id": "req-proj",
                "refresh": {
                    "triggered": True,
                    "reason": "compile_triggering_change",
                    "paths_changed": [],
                    "skipped_reason": "",
                    "settle_outcome": "dispatched",
                    "elapsed_ms": 4,
                },
            }
            with mock.patch.object(
                unity_puer_exec_runtime.unity_session,
                "ensure_session_ready",
                side_effect=[_FakeSession(), unity_session.UnityStalledError("stalled")],
            ), mock.patch.object(
                unity_puer_exec_runtime,
                "_ensure_project_session_ready_after_refresh",
                side_effect=unity_session.UnityStalledError("stalled"),
            ), mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(unity_puer_exec.EXIT_RUNNING, json.dumps(refresh_body), ""),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(
                    [
                        "exec",
                        "--project-path", str(project),
                        "--file", str(script_path),
                        "--request-id", "req-proj",
                    ]
                )

        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["phase"], "refreshing")
        steps = body["next_steps"]
        wait_step = next(step for step in steps if step["command"] == "wait-for-exec")
        self.assertEqual(wait_step["argv"][:2], ["unity-puer-exec", "wait-for-exec"])
        self.assertIn("--project-path", wait_step["argv"])
        self.assertNotIn("refresh_unsettled", [step["command"] for step in steps])
        self.assertEqual(exit_code, unity_puer_exec.EXIT_RUNNING)


class PlayModeCommandTests(unittest.TestCase):
    """Unit coverage for play / pause / stop (see the play-mode-control change)."""

    BASE_URL = "http://127.0.0.1:55231"
    COMPILE_APPEAR = unity_session.DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS

    def _args(self, command, *extra):
        parser = unity_puer_exec.surface.build_parser()
        return parser.parse_args([command, "--base-url", self.BASE_URL, *extra])

    def _health(self, play_state, generation=0, pending="not_pending"):
        return {
            "ok": True,
            "status": "ready",
            "play_state": play_state,
            "compile_generation": generation,
            "refresh": {
                "pending": pending,
                "suppressed": False,
                "suppressed_reason": "",
                "script_changes_while_playing": "unknown",
            },
        }

    def _refresh_body(self, triggered=False):
        return {
            "ok": True,
            "status": "completed",
            "refresh": {
                "triggered": triggered,
                "reason": "",
                "paths_changed": [],
                "skipped_reason": "",
                "settle_outcome": "not_attempted",
                "elapsed_ms": 0,
            },
        }

    def _play_mode_body(self, play_state="entering", ok=True, status="completed", project_setting=False):
        return {
            "ok": ok,
            "status": status,
            "play_state": play_state,
            "project_run_in_background": project_setting,
            "forced_run_in_background": ok,
        }

    def _default_invoke_map(self, **overrides):
        calls = {"play-mode": [], "refresh": []}
        play_state_holder = {"value": "entering"}

        def refresh_handler(_payload):
            return (0, self._refresh_body(triggered=False))

        def play_mode_handler(payload):
            calls["play-mode"].append(payload)
            return (0, self._play_mode_body(play_state=play_state_holder["value"]))

        invoke_map = {
            "refresh": refresh_handler,
            "play-mode": play_mode_handler,
            "get-compile-errors": lambda _payload: (0, {"ok": True, "status": "completed", "total": 0}),
        }
        invoke_map.update(overrides)
        return invoke_map, calls, play_state_holder

    def _run(self, handler, args, health_sequence, invoke_map, extra_patches=()):
        clock = _FakeClock()
        seq = list(health_sequence)

        def probe(_base_url, _timeout):
            item = seq.pop(0) if len(seq) > 1 else seq[0]
            if item is None:
                return None, "connection refused"
            return item, None

        def invoke(command, _base_url, payload, _wait_timeout_ms, transport=None):
            spec = invoke_map.get(command)
            if spec is None:
                return 12, json.dumps({"ok": False, "status": "not_available", "error": command}), ""
            if callable(spec):
                spec = spec(payload)
            if isinstance(spec, tuple) and len(spec) == 3:
                return spec
            exit_code, body = spec
            return exit_code, json.dumps(body), ""

        patches = [
            mock.patch.object(unity_puer_exec_runtime, "time", clock),
            mock.patch.object(unity_session, "probe_health_payload", side_effect=probe),
            mock.patch.object(unity_puer_exec_runtime.direct_exec_client, "invoke_command", side_effect=invoke),
        ]
        patches.extend(extra_patches)
        for patch in patches:
            patch.start()
        try:
            return handler(args)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def _sequence_play_mode(self, calls, specs):
        """A play-mode handler returning ``specs`` in order (the last repeats)."""
        seq = list(specs)

        def handler(payload):
            calls["play-mode"].append(payload)
            return seq.pop(0) if len(seq) > 1 else seq[0]

        return handler

    def _transport_drop_body(self, operation="play-mode"):
        """The boundary payload for an empty/unparseable response body."""
        return {
            "ok": False,
            "status": "empty_response",
            "operation": operation,
            "error": (
                "The control endpoint returned an empty or unparseable response body; "
                "the response could not be decoded as JSON."
            ),
            "exit_code": 12,
            "exit_code_meaning": "the control endpoint answered without a usable response body",
        }

    # --- play ---

    def test_play_settles_cleanly_then_reaches_playing(self):
        invoke_map, calls, holder = self._default_invoke_map()
        code, stdout, stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("edit"), self._health("entering"), self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0, stderr)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["play_state"], "playing")
        self.assertEqual(body["result"]["transition"], "performed")
        self.assertEqual(body["result"]["run_in_background"]["forced"], True)
        self.assertIn("--no-run-in-background", body["result"]["run_in_background"]["option"])
        self.assertEqual(len(calls["play-mode"]), 1)
        self.assertTrue(calls["play-mode"][0]["force_run_in_background"])

    def test_play_no_run_in_background_keeps_the_project_setting(self):
        invoke_map, calls, _holder = self._default_invoke_map()
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play", "--no-run-in-background"),
            [self._health("edit"), self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["run_in_background"]["forced"], False)
        self.assertFalse(calls["play-mode"][0]["force_run_in_background"])

    def test_play_aborts_on_compile_error_without_entering_play_mode(self):
        calls = {"play-mode": []}
        invoke_map = {
            "refresh": lambda _p: (
                unity_puer_exec.EXIT_UNITY_COMPILE_ERROR,
                {"ok": False, "status": "unity_compile_error", "compile_errors_total": 1, "compile_messages": []},
            ),
            "play-mode": lambda payload: calls["play-mode"].append(payload),
        }
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("edit")],
            invoke_map,
        )
        self.assertEqual(code, unity_puer_exec.EXIT_UNITY_COMPILE_ERROR)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_compile_error")
        self.assertEqual(calls["play-mode"], [])

    def test_play_already_playing_is_already_in_state(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "playing"
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["transition"], "already_in_state")

    def test_play_resumes_a_paused_editor(self):
        invoke_map, _calls, _holder = self._default_invoke_map()
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("paused"), self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["transition"], "resumed")
        self.assertEqual(body["result"]["play_state"], "playing")

    def test_play_waits_across_a_domain_reload_during_entering(self):
        invoke_map, _calls, _holder = self._default_invoke_map()
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("edit"), None, None, self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["play_state"], "playing")

    def test_play_retries_a_dropped_endpoint_and_recovers(self):
        invoke_map, calls, _holder = self._default_invoke_map()
        invoke_map["play-mode"] = self._sequence_play_mode(
            calls,
            [(12, self._transport_drop_body()), (0, self._play_mode_body(play_state="entering"))],
        )
        code, stdout, stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play", "--timeout-seconds", "5"),
            [self._health("edit"), self._health("edit"), self._health("entering"), self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(calls["play-mode"]), 2)
        self.assertEqual(json.loads(stdout)["result"]["play_state"], "playing")

    def test_play_dropped_endpoint_without_recovery_reports_the_formal_exit_code(self):
        invoke_map, calls, _holder = self._default_invoke_map()
        invoke_map["play-mode"] = self._sequence_play_mode(calls, [(12, self._transport_drop_body())])
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play", "--timeout-seconds", "1"),
            [self._health("edit"), self._health("edit")],
            invoke_map,
        )
        self.assertEqual(code, 12)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "empty_response")
        self.assertGreaterEqual(len(calls["play-mode"]), 2)

    def test_pause_non_transport_failure_is_not_retried_and_preserves_exit_code(self):
        blocker = {"type": "safe_mode_dialog", "scope": "play-mode"}
        invoke_map, calls, _holder = self._default_invoke_map()
        invoke_map["play-mode"] = self._sequence_play_mode(
            calls,
            [
                (
                    19,
                    {
                        "ok": False,
                        "status": "modal_blocked",
                        "error": "a modal dialog is blocking play mode",
                        "blocker": blocker,
                    },
                )
            ],
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_pause,
            self._args("pause", "--timeout-seconds", "5"),
            [self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, unity_puer_exec.EXIT_MODAL_BLOCKED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        self.assertEqual(body["blocker"], blocker)
        self.assertEqual(len(calls["play-mode"]), 1)

    def test_play_timeout_returns_running_with_current_state(self):
        invoke_map, _calls, _holder = self._default_invoke_map()
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play", "--timeout-seconds", "2"),
            [self._health("edit"), self._health("entering")],
            invoke_map,
        )
        self.assertEqual(code, unity_puer_exec.EXIT_RUNNING)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["result"]["play_state"], "entering")
        self.assertTrue(any(step["command"] == "play" for step in body["next_steps"]))

    # --- pause ---

    def test_pause_from_edit_mode_is_rejected(self):
        invoke_map, _calls, _holder = self._default_invoke_map(
            **{"play-mode": lambda _p: (1, {"ok": False, "status": "invalid_play_state", "play_state": "edit"})}
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_pause,
            self._args("pause"),
            [self._health("edit")],
            invoke_map,
        )
        self.assertEqual(code, 1)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "invalid_play_state")
        self.assertEqual(body["result"]["play_state"], "edit")
        self.assertTrue(any(step["command"] == "play" for step in body["next_steps"]))

    def test_pause_reaches_paused(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "paused"
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_pause,
            self._args("pause"),
            [self._health("playing"), self._health("paused")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["play_state"], "paused")
        self.assertEqual(body["result"]["transition"], "performed")

    # --- stop ---

    def test_stop_from_paused_reports_no_compile_observed(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "edit"
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop"),
            [self._health("paused"), self._health("edit")],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["play_state"], "edit")
        self.assertEqual(body["result"]["transition"], "performed")
        self.assertEqual(body["result"]["compile"]["outcome"], "no_compile_observed")
        self.assertEqual(body["result"]["compile"]["compile_errors_total"], 0)

    def test_stop_with_pending_change_settles_the_compile(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "edit"
        cycle = mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={"outcome": unity_puer_exec_runtime.COMPILE_OUTCOME_READY, "observed_health": [], "api_updater_declines": 0},
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop"),
            [self._health("playing", generation=5, pending="pending"), self._health("edit", generation=5, pending="pending")],
            invoke_map,
            extra_patches=[cycle],
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["compile"]["outcome"], "compile_settled")
        self.assertNotIn("edge", body["result"]["compile"])

    def test_stop_generation_advance_hidden_behind_the_exit_reload(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "edit"
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop", "--timeout-seconds", "5"),
            [self._health("playing", generation=5), None, None, self._health("edit", generation=6)],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["compile"]["outcome"], "compile_settled")
        self.assertEqual(body["result"]["compile"]["edge"], "generation_advance")

    def test_stop_not_pending_with_a_generation_advance_still_settles(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "edit"
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop"),
            [self._health("playing", generation=5, pending="not_pending"), self._health("edit", generation=6)],
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["compile"]["outcome"], "compile_settled")
        self.assertEqual(body["result"]["compile"]["edge"], "generation_advance")

    def test_stop_tolerates_a_long_unreachable_exit_window(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "edit"
        sequence = [self._health("playing")] + [None] * 150 + [self._health("edit")]
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop", "--timeout-seconds", "5"),
            sequence,
            invoke_map,
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["play_state"], "edit")

    def test_stop_with_compile_errors_stays_completed_with_follow_up(self):
        invoke_map, _calls, holder = self._default_invoke_map(
            **{"get-compile-errors": lambda _p: (0, {"ok": True, "status": "completed", "total": 3})}
        )
        holder["value"] = "edit"
        cycle = mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={"outcome": unity_puer_exec_runtime.COMPILE_OUTCOME_READY, "observed_health": [], "api_updater_declines": 0},
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop"),
            [self._health("playing", generation=5, pending="pending"), self._health("edit", generation=5, pending="pending")],
            invoke_map,
            extra_patches=[cycle],
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["result"]["compile"]["compile_errors_total"], 3)
        self.assertEqual(body["next_steps"][0]["command"], "get-compile-errors")

    def test_stop_reports_a_modal_blocker(self):
        invoke_map, _calls, holder = self._default_invoke_map()
        holder["value"] = "playing"
        blocker = mock.patch.object(
            unity_puer_exec_runtime, "_detect_exec_modal_blocker", return_value={"type": "safe_mode_dialog"}
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_stop,
            self._args("stop", "--timeout-seconds", "1"),
            [self._health("playing")],
            invoke_map,
            extra_patches=[blocker],
        )
        self.assertEqual(code, unity_puer_exec.EXIT_MODAL_BLOCKED)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        commands = [step["command"] for step in body["next_steps"]]
        self.assertIn("get-blocker-state", commands)
        self.assertIn("resolve-blocker", commands)

    def test_absent_play_mode_endpoint_maps_to_version_mismatch(self):
        invoke_map, _calls, _holder = self._default_invoke_map(
            **{
                "play-mode": lambda _p: (
                    12,
                    {"ok": False, "status": "not_available", "error": "HTTP Error 404", "http_status": 404},
                )
            }
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_pause,
            self._args("pause"),
            [self._health("playing")],
            invoke_map,
        )
        self.assertEqual(code, unity_puer_exec.direct_exec_client.EXIT_VERSION_MISMATCH)
        body = json.loads(stdout)
        self.assertEqual(body["status"], "version_mismatch")

    def test_play_discloses_a_pre_settle_refresh(self):
        refresh_calls = {"count": 0}
        play_state_holder = {"value": "entering"}

        def refresh_handler(_payload):
            refresh_calls["count"] += 1
            if refresh_calls["count"] == 1:
                return (
                    0,
                    {
                        "ok": True,
                        "status": "running",
                        "phase": "refreshing",
                        "refresh": {
                            "triggered": True,
                            "reason": "code_change",
                            "paths_changed": ["X:/project/Assets/A.cs"],
                            "skipped_reason": "",
                            "settle_outcome": "dispatched",
                            "elapsed_ms": 1,
                        },
                    },
                )
            return (0, self._refresh_body(triggered=False))

        invoke_map = {
            "refresh": refresh_handler,
            "play-mode": lambda payload: (
                0,
                self._play_mode_body(play_state=play_state_holder["value"]),
            ),
        }
        cycle = mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={
                "outcome": unity_puer_exec_runtime.COMPILE_OUTCOME_READY,
                "observed_health": [],
                "api_updater_declines": 0,
            },
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("edit"), self._health("playing")],
            invoke_map,
            extra_patches=[cycle],
        )
        self.assertEqual(code, 0)
        body = json.loads(stdout)
        self.assertEqual(body["refresh"]["triggered"], True)
        self.assertEqual(body["result"]["play_state"], "playing")

    def test_play_aborts_when_the_compile_gate_reports_errors_after_a_refresh(self):
        """A triggered refresh that settles into a failing build still aborts play."""
        refresh_calls = {"count": 0}

        def refresh_handler(_payload):
            refresh_calls["count"] += 1
            if refresh_calls["count"] == 1:
                return (
                    0,
                    {
                        "ok": True,
                        "status": "running",
                        "phase": "refreshing",
                        "refresh": {
                            "triggered": True,
                            "reason": "compile_triggering_change",
                            "paths_changed": ["X:/project/Assets/A.cs"],
                            "skipped_reason": "",
                            "settle_outcome": "dispatched",
                            "elapsed_ms": 1,
                        },
                    },
                )
            return (
                unity_puer_exec.EXIT_UNITY_COMPILE_ERROR,
                {"ok": False, "status": "unity_compile_error", "compile_errors_total": 2, "compile_messages": []},
            )

        cycle = mock.patch.object(
            unity_puer_exec_runtime,
            "wait_for_compile_cycle",
            return_value={
                "outcome": unity_puer_exec_runtime.COMPILE_OUTCOME_READY,
                "observed_health": [],
                "api_updater_declines": 0,
            },
        )
        code, stdout, _stderr = self._run(
            unity_puer_exec_runtime.run_play,
            self._args("play"),
            [self._health("edit")],
            {"refresh": refresh_handler},
            extra_patches=[cycle],
        )
        self.assertEqual(code, unity_puer_exec.EXIT_UNITY_COMPILE_ERROR)
        self.assertEqual(json.loads(stdout)["status"], "unity_compile_error")
        self.assertEqual(refresh_calls["count"], 2)

    # --- help / guidance ---

    def test_play_pause_stop_answer_every_help_tier(self):
        for command in ("play", "pause", "stop"):
            for flag in ("--help", "--help-args", "--help-status"):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([command, flag])
                self.assertEqual(exit_code, 0, (command, flag, stderr))
                self.assertTrue(stdout.strip(), (command, flag))

    def test_top_level_help_lists_play_mode_commands(self):
        exit_code, stdout, _stderr = unity_puer_exec.run_cli(["--help"])
        self.assertEqual(exit_code, 0)
        self.assertIn("play: enter play mode", stdout)
        self.assertIn("pause: pause a playing Editor", stdout)
        self.assertIn("stop: leave play mode", stdout)
        # `stop` must be distinguishable from closing the Editor.
        self.assertIn("Does not close the Editor", stdout)

    def test_play_help_discloses_run_in_background_override_and_option(self):
        _code, stdout, _stderr = unity_puer_exec.run_cli(["play", "--help"])
        self.assertIn("runInBackground", stdout)
        self.assertIn("Player Settings", stdout)
        _code, args_stdout, _stderr = unity_puer_exec.run_cli(["play", "--help-args"])
        self.assertIn("--no-run-in-background", args_stdout)

    def test_play_mode_exit_guidance_uses_stop_not_exec(self):
        commands = [step["command"] for step in help_surface._PLAY_MODE_EXIT_STEPS]
        self.assertEqual(commands, ["stop"])
        for key in (("exec", "compile_blocked_by_play_mode"), ("wait-for-exec", "compile_blocked_by_play_mode")):
            entry_steps = [step["command"] for step in help_surface.WARNING_GUIDANCE_MATRIX[key]["next_steps"]]
            self.assertEqual(entry_steps, ["stop"], key)
        compile_blocked_steps = [
            step["command"] for step in help_surface.GUIDANCE_MATRIX[("wait-for-compile", "compile_blocked")]["next_steps"]
        ]
        self.assertEqual(compile_blocked_steps, ["stop"])


if __name__ == "__main__":
    unittest.main()
