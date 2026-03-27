import json
import os
import time
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
TOOLS_DIR = REPO_ROOT / "tools"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prepare_validation_host  # type: ignore
import cleanup_validation_host  # type: ignore
import unity_puer_exec  # type: ignore
import unity_session  # type: ignore
import unity_session_logs  # type: ignore


RUN_REAL_HOST_TESTS_ENV = "UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS"
WAIT_TIMEOUT_MS = 1000
READY_TIMEOUT_SECONDS = 240
ACTIVITY_TIMEOUT_SECONDS = 60
MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"


def _real_host_tests_enabled():
    value = os.environ.get(RUN_REAL_HOST_TESTS_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _require_real_host_project_path():
    try:
        project_path = prepare_validation_host.resolve_project_path()
    except ValueError as exc:
        raise unittest.SkipTest(str(exc))
    if not project_path.exists():
        raise unittest.SkipTest("validation host project path does not exist: {}".format(project_path))
    manifest_path = prepare_validation_host.project_path_to_manifest_path(project_path)
    if not manifest_path.exists():
        raise unittest.SkipTest("validation host manifest is missing: {}".format(manifest_path))
    return project_path


def _require_unity_editor(project_path):
    try:
        return unity_session._resolve_unity_exe_path(project_path, None)
    except unity_session.UnityLaunchError as exc:
        raise unittest.SkipTest(str(exc))


def _run_cli(argv):
    exit_code, stdout, stderr = unity_puer_exec.run_cli(argv)
    body = stdout or stderr
    payload = json.loads(body) if body else None
    return exit_code, payload, stdout, stderr


def _warm_up_project_exec(project_path, unity_exe_path, include_diagnostics=False):
    script = "export default function run(ctx) { return { probe: 'warmup', request_id: ctx.request_id }; }"
    argv = [
        "exec",
        "--project-path",
        str(project_path),
        "--unity-exe-path",
        str(unity_exe_path),
        "--wait-timeout-ms",
        str(WAIT_TIMEOUT_MS),
        "--code",
        script,
    ]
    if include_diagnostics:
        argv.append("--include-diagnostics")
    exit_code, payload, stdout, stderr = _run_cli(argv)
    if payload is not None and payload.get("status") == "running":
        exit_code, payload, stdout, stderr = _run_cli(
            [
                "wait-for-exec",
                "--project-path",
                str(project_path),
                "--unity-exe-path",
                str(unity_exe_path),
                "--request-id",
                payload["request_id"],
                "--wait-timeout-ms",
                str(READY_TIMEOUT_SECONDS * 1000),
            ] + (["--include-diagnostics"] if include_diagnostics else [])
        )
    return exit_code, payload, stdout, stderr


def _ensure_clean_test_boundary(project_path):
    attempts = 0
    while attempts < 3:
        attempts += 1
        exit_code, payload, _, _ = _run_cli(
            [
                "ensure-stopped",
                "--project-path",
                str(project_path),
                "--timeout-seconds",
                "5",
                "--include-diagnostics",
            ]
        )
        if exit_code == 0:
            return
        if attempts == 2:
            _run_cli(
                [
                    "ensure-stopped",
                    "--project-path",
                    str(project_path),
                    "--timeout-seconds",
                    "1",
                    "--immediate-kill",
                    "--include-diagnostics",
                ]
            )
        time.sleep(1.0)
    raise AssertionError("failed to establish a clean real-host boundary: {}".format(payload))


class RealHostIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _real_host_tests_enabled():
            raise unittest.SkipTest(
                "{} is not enabled; set {}=1 to run real-host integration tests.".format(
                    RUN_REAL_HOST_TESTS_ENV,
                    RUN_REAL_HOST_TESTS_ENV,
                )
            )
        cls.project_path = _require_real_host_project_path()
        cls.unity_exe_path = _require_unity_editor(cls.project_path)

    def setUp(self):
        _ensure_clean_test_boundary(self.project_path)
        prepare_validation_host.main(["--project-path", str(self.project_path)])
        cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)

    def tearDown(self):
        try:
            _ensure_clean_test_boundary(self.project_path)
        except Exception:
            pass
        try:
            cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)
        except Exception:
            pass

    def test_exec_checkpoint_observation_chain_against_real_host(self):
        correlation_id = "sync-{}".format(os.getpid())
        script = "\n".join(
            [
                "export default function run(ctx) {",
                "const correlation_id = {!r};".format(correlation_id),
                "console.log('[UnityPuerExecResult] ' + JSON.stringify({ correlation_id, probe: 'integration', ok: true }));",
                "return { correlation_id, probe: 'integration' };",
                "}",
            ]
        )

        warmup_exit_code, warmup_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(warmup_exit_code, 0, warmup_payload)
        self.assertEqual(warmup_payload["status"], "completed")
        self.assertEqual(warmup_payload["result"]["probe"], "warmup")

        repeat_warmup_exit_code, repeat_warmup_payload, _, _ = _warm_up_project_exec(
            self.project_path,
            self.unity_exe_path,
            include_diagnostics=True,
        )
        self.assertEqual(repeat_warmup_exit_code, 0, repeat_warmup_payload)
        self.assertEqual(repeat_warmup_payload["status"], "completed")
        self.assertEqual(repeat_warmup_payload["result"]["probe"], "warmup")
        self.assertIn("log_range", repeat_warmup_payload)

        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                script,
            ]
        )
        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "completed")
        self.assertIn("log_range", exec_payload)
        self.assertGreaterEqual(exec_payload["log_range"]["start"], 0)
        self.assertGreaterEqual(exec_payload["log_range"]["end"], exec_payload["log_range"]["start"])
        self.assertEqual(exec_payload["result"]["correlation_id"], correlation_id)

        wait_result_exit_code, wait_result_payload, _, _ = _run_cli(
            [
                "wait-for-result-marker",
                "--project-path",
                str(self.project_path),
                "--correlation-id",
                correlation_id,
                "--start-offset",
                str(exec_payload["log_range"]["start"]),
                "--timeout-seconds",
                "30",
                "--activity-timeout-seconds",
                str(ACTIVITY_TIMEOUT_SECONDS),
            ]
        )
        self.assertEqual(wait_result_exit_code, 0, wait_result_payload)
        self.assertEqual(wait_result_payload["result"]["status"], "result_marker_matched")
        self.assertEqual(wait_result_payload["result"]["marker"]["correlation_id"], correlation_id)
        self.assertEqual(wait_result_payload["result"]["marker"]["probe"], "integration")

        wait_pattern_exit_code, wait_pattern_payload, _, _ = _run_cli(
            [
                "wait-for-log-pattern",
                "--project-path",
                str(self.project_path),
                "--pattern",
                MARKER_PATTERN,
                "--extract-json-group",
                "1",
                "--start-offset",
                str(exec_payload["log_range"]["start"]),
                "--timeout-seconds",
                "30",
                "--activity-timeout-seconds",
                str(ACTIVITY_TIMEOUT_SECONDS),
            ]
        )
        self.assertEqual(wait_pattern_exit_code, 0, wait_pattern_payload)
        self.assertEqual(wait_pattern_payload["result"]["status"], "log_pattern_matched")
        self.assertEqual(wait_pattern_payload["result"]["extracted_json"]["correlation_id"], correlation_id)
        self.assertEqual(wait_pattern_payload["result"]["extracted_json"]["probe"], "integration")

    def test_exec_rejects_legacy_fragment_script_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "return 1;",
            ]
        )

        self.assertEqual(exec_exit_code, 1, exec_payload)
        self.assertEqual(exec_payload["status"], "failed")
        self.assertEqual(exec_payload["error"], "missing_default_export")
        self.assertIn("export default function (ctx)", exec_payload["error_detail"])
        self.assertIn("return null;", exec_payload["error_detail"])

    def test_exec_rejects_promise_return_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "export default async function run(ctx) { return 1; }",
            ]
        )

        self.assertEqual(exec_exit_code, 1, exec_payload)
        self.assertEqual(exec_payload["status"], "failed")
        self.assertIn("async_result_not_supported", exec_payload["error"])

    def test_exec_globals_are_visible_across_requests_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        first_exit_code, first_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "export default function run(ctx) { ctx.globals.counter = (ctx.globals.counter || 0) + 1; return { counter: ctx.globals.counter }; }",
            ]
        )
        self.assertEqual(first_exit_code, 0, first_payload)
        self.assertEqual(first_payload["status"], "completed")
        self.assertEqual(first_payload["result"]["counter"], 1)

        second_exit_code, second_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "export default function run(ctx) { ctx.globals.counter = (ctx.globals.counter || 0) + 1; return { counter: ctx.globals.counter }; }",
            ]
        )
        self.assertEqual(second_exit_code, 0, second_payload)
        self.assertEqual(second_payload["status"], "completed")
        self.assertEqual(second_payload["result"]["counter"], 2)

    def test_exec_script_args_are_visible_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--script-args",
                '{"count":2,"name":"codex"}',
                "--code",
                "export default function run(ctx) { return { args: ctx.args, greeting: 'hi ' + ctx.args.name, count: ctx.args.count }; }",
            ]
        )

        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "completed")
        self.assertEqual(exec_payload["result"]["args"], {"count": 2, "name": "codex"})
        self.assertEqual(exec_payload["result"]["greeting"], "hi codex")
        self.assertEqual(exec_payload["result"]["count"], 2)

    def test_wait_for_exec_reports_modified_scene_modal_blocker_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        request_id = "modal-modified-{}".format(os.getpid())
        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const SceneManager = puer.loadType('UnityEngine.SceneManagement.SceneManager');",
                        "  const EditorSceneManager = puer.loadType('UnityEditor.SceneManagement.EditorSceneManager');",
                        "  const scene = SceneManager.GetActiveScene();",
                        "  EditorSceneManager.MarkSceneDirty(scene);",
                        "  EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo();",
                        "  return { request_id: ctx.request_id };",
                        "}",
                    ]
                ),
            ]
        )

        self.assertIn(exec_exit_code, {unity_puer_exec.EXIT_NOT_AVAILABLE, unity_puer_exec.EXIT_MODAL_BLOCKED}, exec_payload)

        wait_exit_code, wait_payload, _, _ = _run_cli(
            [
                "wait-for-exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
            ]
        )

        self.assertEqual(wait_exit_code, unity_puer_exec.EXIT_MODAL_BLOCKED, wait_payload)
        self.assertEqual(wait_payload["status"], "modal_blocked")
        self.assertEqual(wait_payload["blocker"]["type"], "save_modified_scenes_prompt")
        self.assertEqual(wait_payload["blocker"]["scope"], "exec")

    def test_exec_timeout_recovery_avoids_disconnect_noise_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        log_source = unity_session.get_log_source(project_path=self.project_path)
        self.assertIsNotNone(log_source)
        _, log_info = log_source
        log_path = Path(log_info["path"])

        request_id = "disconnect-recover-{}".format(os.getpid())
        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const Thread = puer.loadType('System.Threading.Thread');",
                        "  Thread.Sleep(7000);",
                        "  return { request_id: ctx.request_id, recovered: true };",
                        "}",
                    ]
                ),
            ]
        )

        self.assertEqual(exec_exit_code, unity_puer_exec.EXIT_NOT_AVAILABLE, exec_payload)
        self.assertEqual(exec_payload["status"], "not_available")
        self.assertEqual(exec_payload["request_id"], request_id)
        self.assertIn("log_range", exec_payload)

        time.sleep(2.0)

        wait_exit_code = None
        wait_payload = None
        for _ in range(6):
            wait_exit_code, wait_payload, _, _ = _run_cli(
                [
                    "wait-for-exec",
                    "--project-path",
                    str(self.project_path),
                    "--unity-exe-path",
                    str(self.unity_exe_path),
                    "--request-id",
                    request_id,
                    "--wait-timeout-ms",
                    str(WAIT_TIMEOUT_MS),
                    "--log-start-offset",
                    str(exec_payload["log_range"]["start"]),
                ]
            )
            if wait_exit_code == 0:
                break
            self.assertEqual(wait_exit_code, unity_puer_exec.EXIT_RUNNING, wait_payload)
            time.sleep(1.0)

        self.assertEqual(wait_exit_code, 0, wait_payload)
        self.assertEqual(wait_payload["status"], "completed")
        self.assertEqual(wait_payload["result"]["request_id"], request_id)
        self.assertTrue(wait_payload["result"]["recovered"])

        _, log_chunk = unity_session_logs.read_editor_log_chunk(log_path, exec_payload["log_range"]["start"])
        self.assertIn("Complete request={}".format(request_id), log_chunk)
        self.assertNotIn("Request handling failed", log_chunk)
        self.assertNotIn("Unable to write data to the transport connection", log_chunk)

    def test_get_blocker_state_reports_save_scene_dialog_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        request_id = "modal-save-scene-{}".format(os.getpid())
        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const EditorSceneManager = puer.loadType('UnityEditor.SceneManagement.EditorSceneManager');",
                        "  const NewSceneSetup = puer.loadType('UnityEditor.SceneManagement.NewSceneSetup');",
                        "  const NewSceneMode = puer.loadType('UnityEditor.SceneManagement.NewSceneMode');",
                        "  const scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);",
                        "  EditorSceneManager.MarkSceneDirty(scene);",
                        "  EditorSceneManager.SaveOpenScenes();",
                        "  return { request_id: ctx.request_id };",
                        "}",
                    ]
                ),
            ]
        )

        blocker_exit_code, blocker_payload, _, _ = _run_cli(
            [
                "get-blocker-state",
                "--project-path",
                str(self.project_path),
            ]
        )

        self.assertEqual(blocker_exit_code, 0, blocker_payload)
        self.assertEqual(blocker_payload["result"]["status"], "modal_blocked")
        self.assertEqual(blocker_payload["result"]["blocker"]["type"], "save_scene_dialog")
        self.assertEqual(blocker_payload["result"]["blocker"]["scope"], "exec")

    def test_resolve_blocker_cancels_modified_scene_prompt_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        request_id = "resolve-modified-{}".format(os.getpid())
        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const SceneManager = puer.loadType('UnityEngine.SceneManagement.SceneManager');",
                        "  const EditorSceneManager = puer.loadType('UnityEditor.SceneManagement.EditorSceneManager');",
                        "  const scene = SceneManager.GetActiveScene();",
                        "  EditorSceneManager.MarkSceneDirty(scene);",
                        "  EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo();",
                        "  return { request_id: ctx.request_id };",
                        "}",
                    ]
                ),
            ]
        )

        resolve_exit_code, resolve_payload, _, _ = _run_cli(
            [
                "resolve-blocker",
                "--project-path",
                str(self.project_path),
                "--action",
                "cancel",
            ]
        )

        self.assertEqual(resolve_exit_code, 0, resolve_payload)
        self.assertEqual(resolve_payload["result"]["status"], "resolved")
        self.assertEqual(resolve_payload["result"]["blocker"]["type"], "save_modified_scenes_prompt")

        wait_exit_code, wait_payload, _, _ = _run_cli(
            [
                "wait-for-exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
            ]
        )

        self.assertEqual(wait_exit_code, 0, wait_payload)
        self.assertEqual(wait_payload["status"], "completed")
        self.assertEqual(wait_payload["result"]["request_id"], request_id)

    def test_resolve_blocker_cancels_save_scene_dialog_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        request_id = "resolve-save-scene-{}".format(os.getpid())
        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const EditorSceneManager = puer.loadType('UnityEditor.SceneManagement.EditorSceneManager');",
                        "  const NewSceneSetup = puer.loadType('UnityEditor.SceneManagement.NewSceneSetup');",
                        "  const NewSceneMode = puer.loadType('UnityEditor.SceneManagement.NewSceneMode');",
                        "  const scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);",
                        "  EditorSceneManager.MarkSceneDirty(scene);",
                        "  EditorSceneManager.SaveOpenScenes();",
                        "  return { request_id: ctx.request_id };",
                        "}",
                    ]
                ),
            ]
        )

        resolve_exit_code, resolve_payload, _, _ = _run_cli(
            [
                "resolve-blocker",
                "--project-path",
                str(self.project_path),
                "--action",
                "cancel",
            ]
        )

        self.assertEqual(resolve_exit_code, 0, resolve_payload)
        self.assertEqual(resolve_payload["result"]["status"], "resolved")
        self.assertEqual(resolve_payload["result"]["blocker"]["type"], "save_scene_dialog")

        wait_exit_code, wait_payload, _, _ = _run_cli(
            [
                "wait-for-exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                request_id,
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
            ]
        )

        self.assertEqual(wait_exit_code, 0, wait_payload)
        self.assertEqual(wait_payload["status"], "completed")
        self.assertEqual(wait_payload["result"]["request_id"], request_id)


if __name__ == "__main__":
    unittest.main()
