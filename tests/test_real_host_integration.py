import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
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
import unity_puer_exec_runtime  # type: ignore
import unity_session  # type: ignore
import unity_session_logs  # type: ignore


RUN_REAL_HOST_TESTS_ENV = "UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS"
WAIT_TIMEOUT_MS = 1000
READY_TIMEOUT_SECONDS = 240
ACTIVITY_TIMEOUT_SECONDS = 60
MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"

# Control-port binding constants. These mirror UnityPuerExecServer.cs
# (PreferredPort / MaxPortAttempts) and the exact log lines the server emits at
# Start(). Keep them in sync with the package if those values change.
PREFERRED_CONTROL_PORT = 55231
CONTROL_PORT_ATTEMPTS = 20
CONTROL_PORT_RANGE_END = PREFERRED_CONTROL_PORT + CONTROL_PORT_ATTEMPTS  # exclusive
BATCH_SKIP_LOG_LINE = "[UnityPuerExec] Skipping control service start in batch-mode process"
READY_LOG_PREFIX = "[UnityPuerExec] Ready on port"
BIND_FAILURE_LOG_PREFIX = "[UnityPuerExec] Failed to bind any port"
BATCH_RUN_TIMEOUT_SECONDS = 600
ROLLOVER_OBSERVE_TIMEOUT_SECONDS = 180


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
    if payload is not None and unity_puer_exec_runtime._running_or_timed_out_response(
        exit_code, json.dumps(payload)
    ):
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


def _probe_control_health(port, timeout_seconds=1.5):
    """Probe /health on a loopback control port; return (payload, error)."""
    return unity_session._probe_health("http://127.0.0.1:{}".format(port), timeout_seconds)


def _health_is_ready_for_project(payload, project_path):
    return bool(
        payload
        and payload.get("ok")
        and payload.get("status") == "ready"
        and unity_session._payload_matches_project(payload, project_path)
    )


def _scan_ready_control_endpoint(project_path, exclude_ports=(), timeout_seconds=1.5):
    """Scan the bounded control-port range for a ready endpoint owned by project_path.

    Returns (base_url, payload) for the first match, else (None, None). This is the
    test's own independent oracle for where the interactive service actually bound,
    used to stage and confirm rollover conditions regardless of the CLI's own
    range-aware resolution.
    """
    for port in range(PREFERRED_CONTROL_PORT, CONTROL_PORT_RANGE_END):
        if port in exclude_ports:
            continue
        base_url = "http://127.0.0.1:{}".format(port)
        payload, _ = _probe_control_health(port, timeout_seconds)
        if _health_is_ready_for_project(payload, project_path):
            return base_url, payload
    return None, None


def _preferred_port_is_free():
    """True if the preferred control port can be bound right now (i.e. nobody holds it)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", PREFERRED_CONTROL_PORT))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def _run_batch_mode_unity(unity_exe_path, project_path, timeout_seconds=BATCH_RUN_TIMEOUT_SECONDS):
    """Launch a one-shot batch-mode Unity process and capture its log.

    Returns (exit_code, log_path, log_text). The caller owns deleting log_path.
    Raises subprocess.TimeoutExpired if the process does not exit in time.
    """
    handle = tempfile.NamedTemporaryFile(prefix="upe-batch-", suffix=".log", delete=False)
    log_path = Path(handle.name)
    handle.close()
    process = subprocess.Popen(
        [
            str(unity_exe_path),
            "-batchMode",
            "-nographics",
            "-quit",
            "-projectPath",
            str(project_path),
            "-logFile",
            str(log_path),
        ]
    )
    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)
        raise
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return exit_code, log_path, text


class _PreferredPortBinder:
    """A retry-binder that races to hold the preferred control port.

    It continuously attempts to bind 127.0.0.1:<preferred port> from a daemon
    thread. At steady state the interactive Editor holds the port, so binds fail
    and retry; during a domain reload the Editor's Stop() releases the port and
    the binder wins it before the post-reload Start() runs, forcing Start() to
    roll over to a later port. Once won, the port is held until stop().
    """

    def __init__(self, port=PREFERRED_CONTROL_PORT, poll_interval=0.005):
        self.port = port
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._bound = threading.Event()
        self._thread = None
        self._sock = None

    def _run(self):
        while not self._stop.is_set():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(("127.0.0.1", self.port))
                sock.listen(1)
            except OSError:
                sock.close()
                time.sleep(self.poll_interval)
                continue
            self._sock = sock
            self._bound.set()
            # Hold the port until asked to release it.
            while not self._stop.is_set():
                time.sleep(0.02)
            try:
                sock.close()
            finally:
                self._sock = None
            return

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def bound(self):
        return self._bound.is_set() and self._sock is not None

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def _nudge_editor_foreground_win32():
    """Best-effort: bring a Unity Editor window to the foreground on win32.

    Only needed as a focus nudge for the touched-script reload fallback when
    Unity's auto-refresh is focus-gated. Returns True if a window was nudged.
    Failures are swallowed -- the server-side refresh path does not require focus.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        unity_pids = set(unity_session._list_unity_pids())
        if not unity_pids:
            return False
        user32 = ctypes.windll.user32
        nudged = {"hwnd": None}

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in unity_pids:
                nudged["hwnd"] = hwnd
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(_callback), 0)
        if nudged["hwnd"] is not None:
            user32.SetForegroundWindow(nudged["hwnd"])
            return True
    except Exception:
        return False
    return False


def _trigger_domain_reload_via_exec(base_url):
    """Force a domain reload by exec-ing RequestScriptReload against base_url.

    The reload tears down the ScriptEnv mid-request, so the exec response may be a
    benign disconnect/not_available -- the caller keys off post-reload health, not
    this return value.
    """
    code = "\n".join(
        [
            "export default function run(ctx) {",
            "  const EditorUtility = puer.loadType('UnityEditor.EditorUtility');",
            "  EditorUtility.RequestScriptReload();",
            "  return { requested: true };",
            "}",
        ]
    )
    return _run_cli(
        [
            "exec",
            "--base-url",
            base_url,
            "--wait-timeout-ms",
            str(WAIT_TIMEOUT_MS),
            "--code",
            code,
        ]
    )


def _trigger_domain_reload_via_touched_script(project_path, unity_exe_path):
    """Fallback reload trigger: touch a host script and force a recompile+reload.

    Writes a uniquely-changing C# file under the validation temp directory and
    runs refresh-before-exec, which drives AssetDatabase.Refresh server-side and
    therefore does not require Editor focus. A best-effort win32 foreground nudge
    is attempted first for environments where auto-refresh is focus-gated.
    """
    _nudge_editor_foreground_win32()
    temp_dir = project_path / "Assets" / "__codex_validation_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    marker = temp_dir / "ControlPortReloadNudge.cs"
    marker.write_text(
        "// Auto-generated reload nudge for control-port rollover regression.\n"
        "internal static class ControlPortReloadNudge {{ internal const long Stamp = {}L; }}\n".format(
            time.time_ns()
        ),
        encoding="utf-8",
    )
    return _run_cli(
        [
            "exec",
            "--project-path",
            str(project_path),
            "--unity-exe-path",
            str(unity_exe_path),
            "--wait-timeout-ms",
            str(WAIT_TIMEOUT_MS),
            "--refresh-before-exec",
            "--code",
            "export default function run(ctx) { return { ok: true }; }",
        ]
    )


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

    def test_component_detection_example_executes_against_real_host(self):
        import help_surface

        script = "\n".join(
            help_surface.WORKFLOW_EXAMPLES["component-detection"]["steps"][0]["script_body"]
        )

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
                script,
            ]
        )

        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "completed")
        result = exec_payload["result"]
        self.assertIsInstance(result["rootCount"], int)
        self.assertGreaterEqual(result["rootCount"], 0)
        self.assertIsInstance(result["results"], list)
        self.assertEqual(len(result["results"]), result["rootCount"])

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

    def test_exec_bare_typeof_reference_error_hints_puer_prefix_against_real_host(self):
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
                "export default function run(ctx) { return $typeof; }",
            ]
        )

        self.assertEqual(exec_exit_code, 1, exec_payload)
        self.assertEqual(exec_payload["status"], "failed")
        self.assertEqual(exec_payload["error"], "ReferenceError: $typeof is not defined")
        self.assertIn("puer.$typeof", exec_payload["situation"])

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

        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "warning")
        self.assertEqual(exec_payload["warning"], "async_result_not_supported")
        self.assertIn("warning_detail", exec_payload)
        self.assertTrue(len(exec_payload["warning_detail"]) > 0)

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



    def test_compile_error_gate_blocks_exec_against_real_host(self):
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        # Write a deliberately broken C# file to trigger compile errors
        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        broken_cs = temp_dir / "BrokenCompileErrorTest.cs"
        broken_cs.write_text(
            "// Deliberate compile error for integration test\n"
            "public class BrokenCompileErrorTest {\n"
            "    public void Broken() {\n"
            "        ThisTypeDoesNotExist x = null;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        try:
            # Trigger recompilation via refresh-before-exec
            exec_exit_code, exec_payload, _, _ = _run_cli(
                [
                    "exec",
                    "--project-path", str(self.project_path),
                    "--unity-exe-path", str(self.unity_exe_path),
                    "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
                    "--refresh-before-exec",
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )
            # The refresh path: CLI does refresh-exec, then polls for readiness,
            # then does actual exec which hits the compile-error gate.
            if unity_puer_exec_runtime._running_or_timed_out_response(
                exec_exit_code, json.dumps(exec_payload) if exec_payload else ""
            ):
                exec_exit_code, exec_payload, _, _ = _run_cli(
                    [
                        "wait-for-exec",
                        "--project-path", str(self.project_path),
                        "--unity-exe-path", str(self.unity_exe_path),
                        "--request-id", exec_payload["request_id"],
                        "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                    ]
                )

            self.assertEqual(exec_exit_code, unity_puer_exec.EXIT_UNITY_COMPILE_ERROR, exec_payload)
            self.assertEqual(exec_payload["status"], "unity_compile_error")
            self.assertIn("session_marker", exec_payload)
            self.assertGreater(exec_payload["compile_errors_total"], 0)
            self.assertIsInstance(exec_payload["compile_messages"], list)
            self.assertGreater(len(exec_payload["compile_messages"]), 0)
            msg = exec_payload["compile_messages"][0]
            self.assertIn("file", msg)
            self.assertIn("line", msg)
            self.assertIn("message", msg)
            self.assertIn("type", msg)

            # get-compile-errors should return matching session_marker
            ce_exit_code, ce_payload, _, _ = _run_cli(
                [
                    "get-compile-errors",
                    "--project-path", str(self.project_path),
                    "--start", "0",
                    "--count", "5",
                ]
            )
            self.assertEqual(ce_exit_code, 0, ce_payload)
            self.assertIn("result", ce_payload)
            self.assertEqual(
                ce_payload["result"]["session_marker"],
                exec_payload["session_marker"],
                "session_marker must match between exec and get-compile-errors",
            )
            self.assertGreater(ce_payload["result"]["total"], 0)

            # get-compile-warnings should also work
            cw_exit_code, cw_payload, _, _ = _run_cli(
                [
                    "get-compile-warnings",
                    "--project-path", str(self.project_path),
                    "--start", "0",
                    "--count", "5",
                ]
            )
            self.assertEqual(cw_exit_code, 0, cw_payload)
            self.assertIn("result", cw_payload)
            self.assertIn("session_marker", cw_payload["result"])

        finally:
            # Clean up the broken file and recompile to restore clean state
            broken_cs.unlink(missing_ok=True)
            _run_cli(
                [
                    "exec",
                    "--project-path", str(self.project_path),
                    "--unity-exe-path", str(self.unity_exe_path),
                    "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
                    "--refresh-before-exec",
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )

    def test_base_url_refresh_before_exec_and_wait_for_compile_against_real_host(self):
        """compile-loop-tooling regression: base-url --refresh-before-exec is accepted
        (no longer project-only) and runs the user script after settling, and
        wait-for-compile brackets the cycle over the same endpoint without staleness."""
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        base_url, _ = _scan_ready_control_endpoint(self.project_path)
        self.assertIsNotNone(base_url, "could not resolve a ready control endpoint for the base-url regression")

        # 1. Base-url refresh-before-exec must no longer be rejected as project-only,
        #    and the terminal response carries the user script result, not {refreshed: true}.
        _nudge_editor_foreground_win32()
        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
                "--refresh-before-exec",
                "--code", "export default function run(ctx) { return { loop: 'base-url-ok' }; }",
            ]
        )
        if exec_payload and unity_puer_exec_runtime._running_or_timed_out_response(
            exec_exit_code, json.dumps(exec_payload)
        ):
            exec_exit_code, exec_payload, _, _ = _run_cli(
                [
                    "wait-for-exec",
                    "--base-url", base_url,
                    "--request-id", exec_payload["request_id"],
                    "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                ]
            )
        self.assertNotEqual(
            (exec_payload or {}).get("error", ""),
            "refresh-before-exec is only valid with --project-path",
            "base-url refresh-before-exec must no longer be rejected",
        )
        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "completed")
        self.assertEqual(exec_payload["result"]["loop"], "base-url-ok")
        self.assertNotIn("refreshed", exec_payload["result"])

        # 2. wait-for-compile over the same endpoint returns a well-formed terminal
        #    outcome and reports the observed /health sequence.
        wfc_exit_code, wfc_payload, _, _ = _run_cli(
            [
                "wait-for-compile",
                "--base-url", base_url,
                "--appear-timeout-seconds", "5",
                "--settle-timeout-seconds", str(READY_TIMEOUT_SECONDS),
                "--include-diagnostics",
            ]
        )
        self.assertEqual(wfc_exit_code, 0, wfc_payload)
        self.assertEqual(wfc_payload["operation"], "wait-for-compile")
        self.assertIn(wfc_payload["result"]["status"], ("compile_settled", "no_compile_observed"))
        self.assertIn("observed_health", wfc_payload.get("diagnostics", {}))

    def test_compile_error_safe_mode_is_transparent_against_real_host(self):
        """When Unity enters Safe Mode, exec surfaces compile errors (not modal_blocked)."""
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        broken_cs = temp_dir / "SafeModeTriggerTest.cs"
        broken_cs.write_text(
            "// Two deliberate errors to increase Safe Mode likelihood\n"
            "public class SafeModeTriggerTest : NonExistentBase {\n"
            "    public void Broken1() { UndeclaredVariable; }\n"
            "    public void Broken2() { AnotherMissing + = 1; }\n"
            "}\n",
            encoding="utf-8",
        )
        try:
            exec_exit_code, exec_payload, _, _ = _run_cli(
                [
                    "exec",
                    "--project-path", str(self.project_path),
                    "--unity-exe-path", str(self.unity_exe_path),
                    "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
                    "--refresh-before-exec",
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )
            if unity_puer_exec_runtime._running_or_timed_out_response(
                exec_exit_code, json.dumps(exec_payload) if exec_payload else ""
            ):
                exec_exit_code, exec_payload, _, _ = _run_cli(
                    [
                        "wait-for-exec",
                        "--project-path", str(self.project_path),
                        "--unity-exe-path", str(self.unity_exe_path),
                        "--request-id", exec_payload["request_id"],
                        "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                    ]
                )

            # The response should be unity_compile_error, never modal_blocked
            self.assertIn(
                exec_exit_code,
                {unity_puer_exec.EXIT_UNITY_COMPILE_ERROR, 0},
                "Safe Mode should surface as unity_compile_error, not modal_blocked."
                " Payload: {}".format(exec_payload),
            )
            if exec_exit_code == unity_puer_exec.EXIT_UNITY_COMPILE_ERROR:
                self.assertEqual(exec_payload["status"], "unity_compile_error")
                self.assertGreater(exec_payload["compile_errors_total"], 0)

        finally:
            broken_cs.unlink(missing_ok=True)
            _run_cli(
                [
                    "exec",
                    "--project-path", str(self.project_path),
                    "--unity-exe-path", str(self.unity_exe_path),
                    "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
                    "--refresh-before-exec",
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )

    def test_batch_mode_process_suppresses_control_service_against_real_host(self):
        """A batch-mode Unity process must skip the control service.

        Prerequisite: the host project must NOT be open in an interactive Editor.
        A batch-mode launch needs the exclusive project lock, so this test skips
        (rather than fails) when any Unity process is already running. The
        inherited setUp force-stops the host Editor, so this normally holds.
        """
        running_pids = unity_session._list_unity_pids()
        if running_pids:
            self.skipTest(
                "host project appears open in an interactive Editor (unity pids={}); "
                "batch-mode launch needs the exclusive project lock".format(running_pids)
            )

        try:
            exit_code, log_path, log_text = _run_batch_mode_unity(
                self.unity_exe_path, self.project_path
            )
        except subprocess.TimeoutExpired:
            self.skipTest("batch-mode Unity did not exit within the timeout")
            return

        try:
            self.assertIn(
                BATCH_SKIP_LOG_LINE,
                log_text,
                "batch-mode log did not record the control-service skip line; "
                "exit_code={} log={}".format(exit_code, log_path),
            )
            self.assertNotIn(
                READY_LOG_PREFIX,
                log_text,
                "batch-mode process unexpectedly reported a control-port bind; log={}".format(log_path),
            )
            self.assertNotIn(
                BIND_FAILURE_LOG_PREFIX,
                log_text,
                "batch-mode process reported a whole-range bind failure; log={}".format(log_path),
            )
        finally:
            log_path.unlink(missing_ok=True)

    def test_control_port_rolls_over_when_preferred_port_occupied_against_real_host(self):
        """An occupied preferred control port must roll over, not fail the scan.

        Stages the exact procedure proven during fix-control-port-bind-fallback
        manual validation: run a retry-binder for the preferred port, force a
        domain reload so the binder wins the port in the Stop()->Start() window,
        then assert the interactive service became ready on a later port.
        """
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        editor_base_url, _ = _scan_ready_control_endpoint(self.project_path)
        if editor_base_url is None:
            self.skipTest("no ready control endpoint for host project; cannot stage rollover")
            return

        # Skip if the preferred port is held by something that is NOT our Editor.
        pre_payload, _ = _probe_control_health(PREFERRED_CONTROL_PORT)
        if pre_payload is not None:
            if not _health_is_ready_for_project(pre_payload, self.project_path):
                self.skipTest(
                    "preferred control port {} is held by an unrelated service".format(PREFERRED_CONTROL_PORT)
                )
                return
        elif not _preferred_port_is_free():
            self.skipTest(
                "preferred control port {} is held by an unrelated process".format(PREFERRED_CONTROL_PORT)
            )
            return

        binder = _PreferredPortBinder()
        binder.start()
        try:
            rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=False)
            if rolled is None:
                # Retry once: the Editor may have reclaimed the preferred port if
                # the binder lost the first race. Use the touched-script trigger.
                rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=True)

            self.assertIsNotNone(
                rolled,
                "interactive service did not roll over to a later port; it may have "
                "reclaimed {} (binder.bound={})".format(PREFERRED_CONTROL_PORT, binder.bound),
            )
            rolled_base_url, rolled_payload = rolled
            self.assertGreater(rolled_payload["port"], PREFERRED_CONTROL_PORT)
            self.assertLess(rolled_payload["port"], CONTROL_PORT_RANGE_END)
            self.assertEqual(rolled_base_url, "http://127.0.0.1:{}".format(rolled_payload["port"]))
            self.assertEqual(rolled_payload.get("base_url"), rolled_base_url)
        finally:
            # Release the preferred port so the Editor can reclaim it on its next reload.
            binder.stop()

    def _stage_rollover(self, binder, editor_base_url, use_touch_fallback):
        """Trigger a reload and watch for a rolled-over ready endpoint.

        Returns (base_url, payload) on a later port, or None if the interactive
        service came back on the preferred port (binder lost the race).
        """
        if use_touch_fallback:
            _trigger_domain_reload_via_touched_script(self.project_path, self.unity_exe_path)
        else:
            _trigger_domain_reload_via_exec(editor_base_url)

        deadline = time.time() + ROLLOVER_OBSERVE_TIMEOUT_SECONDS
        while time.time() < deadline:
            base_url, payload = _scan_ready_control_endpoint(
                self.project_path, exclude_ports=(PREFERRED_CONTROL_PORT,)
            )
            if base_url is not None:
                return base_url, payload
            # If the service is back on the preferred port and the binder is not
            # holding it, the Editor reclaimed it -- abandon and let the caller retry.
            pref_payload, _ = _probe_control_health(PREFERRED_CONTROL_PORT)
            if _health_is_ready_for_project(pref_payload, self.project_path) and not binder.bound:
                return None
            time.sleep(1.0)
        return None

    def test_exec_discovers_rolled_over_control_port_against_real_host(self):
        """exec --project-path must reach an Editor that rolled over to a non-preferred port.

        Stages the same rollover as the control-port rollover test, then -- while
        the preferred port is still held by the binder -- runs exec --project-path
        with no --base-url. Range-aware session discovery must find the rolled-over
        endpoint instead of waiting on the preferred port. Before this change the
        CLI only probed the preferred port and the session artifact, so it would
        fail or time out staging exactly this multi-instance condition.
        """
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        editor_base_url, _ = _scan_ready_control_endpoint(self.project_path)
        if editor_base_url is None:
            self.skipTest("no ready control endpoint for host project; cannot stage rollover")
            return

        pre_payload, _ = _probe_control_health(PREFERRED_CONTROL_PORT)
        if pre_payload is not None:
            if not _health_is_ready_for_project(pre_payload, self.project_path):
                self.skipTest(
                    "preferred control port {} is held by an unrelated service".format(PREFERRED_CONTROL_PORT)
                )
                return
        elif not _preferred_port_is_free():
            self.skipTest(
                "preferred control port {} is held by an unrelated process".format(PREFERRED_CONTROL_PORT)
            )
            return

        binder = _PreferredPortBinder()
        binder.start()
        try:
            rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=False)
            if rolled is None:
                rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=True)
            if rolled is None:
                self.skipTest("could not stage a control-port rollover; binder lost the race")
                return

            rolled_base_url, rolled_payload = rolled
            self.assertGreater(rolled_payload["port"], PREFERRED_CONTROL_PORT)

            # The Editor is now on a non-preferred port and the binder still holds
            # the preferred port. exec --project-path (no --base-url) must discover
            # the rolled-over endpoint via the range scan.
            self.assertTrue(binder.bound, "binder no longer holds the preferred port; precondition lost")
            exec_exit_code, exec_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
            self.assertEqual(
                exec_exit_code,
                0,
                "exec --project-path failed to discover the rolled-over endpoint {}: {}".format(
                    rolled_base_url, exec_payload
                ),
            )
        finally:
            # Release the preferred port so the Editor can reclaim it on its next reload.
            binder.stop()


if __name__ == "__main__":
    unittest.main()
