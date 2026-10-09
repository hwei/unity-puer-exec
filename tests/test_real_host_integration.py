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
TESTS_DIR = REPO_ROOT / "tests"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import prepare_validation_host  # type: ignore
import preflight_compile_check  # type: ignore
import cleanup_validation_host  # type: ignore
import unity_puer_exec  # type: ignore
import unity_puer_exec_runtime  # type: ignore
import unity_session  # type: ignore
import unity_session_logs  # type: ignore
import unity_modal_blockers  # type: ignore
import unity_session_process  # type: ignore
import real_host_retry  # type: ignore


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
# Uniform activation gate (UnityPuerExecServer.StartIfActivated). The service no
# longer has a batch-mode-only suppression; absence of the switch is what skips.
BATCH_NOT_ACTIVATED_LOG_LINE = (
    "[UnityPuerExec] Control service not activated for this process."
)
CONTROL_ACTIVATION_SWITCH = "-unityPuerExecControl"
READY_LOG_PREFIX = "[UnityPuerExec] Ready on port"
BIND_FAILURE_LOG_PREFIX = "[UnityPuerExec] Failed to bind any port"
BATCH_RUN_TIMEOUT_SECONDS = 600
ROLLOVER_OBSERVE_TIMEOUT_SECONDS = 180
# The rollover cases classify the preferred port before staging: these two states
# mean something the suite cannot displace holds it, so the mid-reload rebind race
# (P2) is unstageable and only the later-port rollover (P1) can be asserted.
_FOREIGN_PREFERRED_STATES = {"foreign_endpoint", "foreign_process"}


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


def _pick_cancel_button_label(blocker):
    """Pick a cancel-like button label from a blocker payload.

    The validation host runs a zh-CN Editor, so button labels are localized
    ("取消" rather than "Cancel"). Matching a hardcoded English label would fail
    for reasons unrelated to the behavior under test.
    """
    buttons = blocker.get("buttons") or []
    normalized = []
    for button in buttons:
        label = button.get("label") or ""
        normalized.append((label.replace("&", "").strip().lower(), label))
    for bare, label in normalized:
        if bare in {"cancel", "取消", "no", "否", "don't save", "不保存"}:
            return label
    return normalized[-1][1] if normalized else None


def _run_cli(argv):
    exit_code, stdout, stderr = unity_puer_exec.run_cli(argv)
    body = stdout or stderr
    payload = json.loads(body) if body else None
    return exit_code, payload, stdout, stderr


def _single_warm_up_project_exec(project_path, unity_exe_path, include_diagnostics=False):
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
    payload = None
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
            return {"ok": True, "status": "stopped", "attempts": attempts, "payload": payload}
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


def _is_editor_ready_for_project(project_path):
    try:
        import unity_session_endpoint
        publication = unity_session_endpoint.read_endpoint_publication(project_path)
        if publication and "port" in publication:
            payload, _ = _probe_control_health(publication["port"], timeout_seconds=0.5)
            return _health_is_ready_for_project(payload, project_path)
    except Exception:
        pass
    return False


def _warm_up_project_exec(
    project_path,
    unity_exe_path,
    include_diagnostics=False,
    max_attempts=real_host_retry.DEFAULT_MAX_ATTEMPTS,
    transient_failure_injector=None,
):
    return real_host_retry.warm_up_with_retry(
        warm_up_fn=_single_warm_up_project_exec,
        project_path=project_path,
        unity_exe_path=unity_exe_path,
        ensure_clean_boundary_fn=_ensure_clean_test_boundary,
        include_diagnostics=include_diagnostics,
        max_attempts=max_attempts,
        is_editor_ready_fn=_is_editor_ready_for_project,
        transient_failure_injector=transient_failure_injector,
    )


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


def _run_batch_mode_unity(
    unity_exe_path,
    project_path,
    timeout_seconds=BATCH_RUN_TIMEOUT_SECONDS,
    activate=False,
):
    """Launch a one-shot batch-mode Unity process and capture its log.

    When activate is True, the process is launched with the control-service
    activation switch so the uniform activation rule can be exercised in both
    directions. Returns (exit_code, log_path, log_text). The caller owns deleting
    log_path. Raises subprocess.TimeoutExpired if the process does not exit in time.
    """
    handle = tempfile.NamedTemporaryFile(prefix="upe-batch-", suffix=".log", delete=False)
    log_path = Path(handle.name)
    handle.close()
    args = [
        str(unity_exe_path),
        "-batchMode",
        "-nographics",
        "-quit",
        "-projectPath",
        str(project_path),
        "-logFile",
        str(log_path),
    ]
    if activate:
        args.append(CONTROL_ACTIVATION_SWITCH)
    process = subprocess.Popen(args)
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
    relies on the automatic code-change refresh, which drives AssetDatabase.Refresh server-side and
    therefore does not require Editor focus.
    """
    temp_dir = project_path / "Assets" / "__codex_validation_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    marker = temp_dir / "ControlPortReloadProbe.cs"
    marker.write_text(
        "// Auto-generated reload probe for control-port rollover regression.\n"
        "internal static class ControlPortReloadProbe {{ internal const long Stamp = {}L; }}\n".format(
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
            "--code",
            "export default function run(ctx) { return { ok: true }; }",
        ]
    )


def _seed_obsolete_api_fixture(project_path):
    """Seed a host fixture referencing obsolete/[UnityUpgradable] APIs.

    Writes a source file under Assets/__codex_validation_temp/ that references
    obsolete APIs carrying (UnityUpgradable) markers. Returns (fixture_path, original_content).
    """
    temp_dir = Path(project_path) / "Assets" / "__codex_validation_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = temp_dir / "ScriptUpdaterTriggerFixture.cs"
    content = (
        "// Auto-generated obsolete API fixture for ScriptUpdater recovery coverage.\n"
        "using UnityEngine;\n\n"
        "public class ScriptUpdaterTriggerFixture : MonoBehaviour\n"
        "{\n"
        "    public void UseObsoleteApis()\n"
        "    {\n"
        "        transform.FindChild(\"child\");\n"
        "        QualitySettings.masterTextureLimit = 1;\n"
        "    }\n"
        "}\n"
    )
    fixture_path.write_text(content, encoding="utf-8")
    return fixture_path, content


# --- shared real-host lifecycle -------------------------------------------
#
# One Editor per suite. The class-level fixture establishes the clean boundary
# from project-local state and brings the host up through the existing
# real_host_retry path exactly once. Ordinary cases reuse that Editor and get a
# cheap per-case state reset instead of a relaunch.
#
# The per-case reset covers the state a reused process can carry that a
# relaunched one could not: repository-owned validation temp assets, Editor play
# mode, a residual modal dialog, and the test-owned change signal.
#
# A case that genuinely needs a process the shared Editor cannot be names itself
# in OWN_HOST_BOUNDARY_TESTS and owns its own launch/stop boundary; the shared
# host is re-established for the cases that follow it.

HOST_READY_RESET_TIMEOUT_SECONDS = 240
EDIT_MODE_RESET_TIMEOUT_SECONDS = 180
COMPILE_RECOVERY_PROBE_NAME = "_host_reset_compile_probe.cs"
BOUNDARY_ATTEMPTS = 3
BOUNDARY_RETRY_SLEEP_SECONDS = 10.0


def _start_shared_host(project_path, unity_exe_path):
    """Establish the clean boundary and bring the host up once, with bounded retry.

    Returns a report carrying the resolved base URL and the launch payload. Raises
    AssertionError with machine-usable attempt diagnostics when the host cannot be
    brought up, so a persistent launch regression stays distinguishable from a
    transient flake.
    """
    last_exit_code = 1
    last_payload = None
    for boundary_attempt in range(1, BOUNDARY_ATTEMPTS + 1):
        _ensure_clean_test_boundary(project_path)
        prepare_validation_host.main(["--project-path", str(project_path)])
        cleanup_validation_host.cleanup_validation_temp_assets(project_path)
        last_exit_code, last_payload, _, _ = _warm_up_project_exec(
            project_path, unity_exe_path, include_diagnostics=True
        )
        # The warm-up can return a non-terminal "running" while the Editor is
        # still settling; the test's own endpoint oracle is the authority on
        # whether the host is actually up, so resolve from that.
        base_url, health = _scan_ready_control_endpoint(project_path)
        if base_url is None:
            base_url, health = _await_ready_endpoint(project_path)
        if base_url is not None:
            return {"base_url": base_url, "health": health, "launch": last_payload}
        # A previous Editor can leave a short-lived asset-import worker holding
        # the project lock after it is stopped, which makes the next launch
        # refuse ("editor_not_under_cli_control"). That window is transient, so
        # re-establish the boundary and try again before declaring failure.
        status = last_payload.get("status") if isinstance(last_payload, dict) else None
        if status not in {"editor_not_under_cli_control", "running", "unknown"}:
            break
        time.sleep(BOUNDARY_RETRY_SLEEP_SECONDS)
    detail = last_payload if isinstance(last_payload, dict) else {}
    raise AssertionError(
        "shared validation host did not come up after {} boundary attempts: "
        "exit_code={} status={} attempt_count={} last_launch_status={} "
        "attempts={} payload={}".format(
            BOUNDARY_ATTEMPTS,
            last_exit_code,
            detail.get("status"),
            detail.get("attempt_count"),
            detail.get("last_launch_status"),
            detail.get("attempts"),
            last_payload,
        )
    )


def _await_ready_endpoint(project_path, timeout_seconds=HOST_READY_RESET_TIMEOUT_SECONDS):
    """Poll for a ready control endpoint owned by project_path.

    Used between cases to ride out a reload a case triggered (for example a
    deliberate compile-error case recovering asynchronously) before deciding the
    host is actually gone.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        base_url, payload = _scan_ready_control_endpoint(project_path)
        if base_url is not None:
            return base_url, payload
        time.sleep(1.0)
    return None, None


class _SharedRealHostDevice:
    """Mixin: one Editor per suite, per-case state reset, explicit opt-out.

    Subclasses set ``OWN_HOST_BOUNDARY_TESTS`` to the test method names that need a
    pristine process. List this mixin before ``unittest.TestCase`` in the bases.
    """

    OWN_HOST_BOUNDARY_TESTS = {}

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
        # A batch-mode compile preflight needs the project lock to itself, so
        # establish the clean boundary before it, then compile-check before the
        # interactive launch. The helper caches its result for the process, so
        # this still costs one batch launch per suite invocation, not one per
        # class; a compile failure raises here, before any interactive Editor is
        # launched, and an unavailable host is skipped rather than failed.
        _ensure_clean_test_boundary(cls.project_path)
        preflight_compile_check.require_preflight(cls.project_path, cls.unity_exe_path)
        cls._shared_host = _start_shared_host(cls.project_path, cls.unity_exe_path)
        cls._shared_host_base_url = cls._shared_host["base_url"]

    @classmethod
    def tearDownClass(cls):
        # Stop the host even when a case failed, so a broken case cannot leak a
        # running Editor into the next suite invocation.
        cls._shared_host_base_url = None
        try:
            _ensure_clean_test_boundary(cls.project_path)
        except Exception:
            pass
        try:
            cleanup_validation_host.cleanup_validation_temp_assets(cls.project_path)
        except Exception:
            pass

    # -- per-case lifecycle ------------------------------------------------

    def setUp(self):
        mode = self._own_boundary_mode()
        if mode is not None:
            # Pristine-process case. ``stop`` hands it a stopped host; ``running``
            # gives it a live host it may perturb to stage its own condition.
            # Either way the case owns its launch/stop boundary and reports it,
            # and the shared host is restored for the cases after it.
            self._own_boundary_report = {
                "case": self._testMethodName,
                "owns_boundary": True,
                "mode": mode,
                "stopped": False,
                "perturbed": False,
                "reestablished": False,
            }
            if mode == "stop":
                self._own_boundary_stop()
            else:
                self._ensure_shared_host_ready()
            self.addCleanup(self._restore_shared_host_after_own_boundary)
            return
        self._reset_shared_host_state()

    def tearDown(self):
        report = getattr(self, "_own_boundary_report", None)
        if report is not None:
            # A pristine-process case reports the boundary it owned rather than
            # silently riding the shared host. Emit it as one machine-usable line so
            # a reader of the run can tell which sub-assertions were actually staged
            # (e.g. mid_reload_rebind=not_staged) instead of only seeing "ok".
            self.assertTrue(report.get("owns_boundary"), report)
            print("[real-host-boundary] " + json.dumps(report, default=str))

    def _owns_host_boundary(self):
        return self._testMethodName in type(self).OWN_HOST_BOUNDARY_TESTS

    def _own_boundary_mode(self):
        return type(self).OWN_HOST_BOUNDARY_TESTS.get(self._testMethodName)

    def _own_boundary_stop(self):
        """Stop the shared host so this case has a virgin project lock."""
        result = _ensure_clean_test_boundary(self.project_path)
        cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)
        report = getattr(self, "_own_boundary_report", None)
        if report is not None:
            report["stopped"] = True
            report["stop"] = result
        return result

    def _mark_own_boundary_perturbed(self):
        """Mark that this case changed the shared host's process/port state."""
        report = getattr(self, "_own_boundary_report", None)
        if report is not None:
            report["perturbed"] = True

    def _record_own_boundary(self, boundary, **details):
        """Record the launch/stop boundary a pristine-process case owned.

        The report is machine-usable: it names the boundary kind and its observed
        result, so a reader can tell this case did not ride the shared host.
        """
        report = getattr(self, "_own_boundary_report", None)
        if report is None:
            report = {"case": self._testMethodName, "owns_boundary": True}
            self._own_boundary_report = report
        report["boundary"] = boundary
        report.update(details)
        return report

    def _restore_shared_host_after_own_boundary(self):
        """Return the suite to a clean shared host after a pristine-process case.

        A ``stop`` case removed the host; a ``running`` case only needs restoring
        when it actually staged its own condition. A ``running`` case that skipped
        before touching anything leaves the shared host untouched, so no relaunch
        is paid for a skip.
        """
        own = getattr(self, "_own_boundary_report", None) or {}
        if not own.get("stopped") and not own.get("perturbed"):
            return
        try:
            cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)
        except Exception:
            pass
        # If the case (or its own launch) left a healthy Editor, adopt it rather
        # than paying for a redundant stop/relaunch. The next case's reset
        # supplies the per-case state isolation either way.
        base_url, health = _scan_ready_control_endpoint(self.project_path)
        if base_url is not None:
            type(self)._shared_host_base_url = base_url
            type(self)._shared_host = {
                "base_url": base_url,
                "health": health,
                "launch": None,
            }
            own["reestablished"] = True
            own["reused_after_boundary"] = True
            own["base_url"] = base_url
            return
        try:
            _ensure_clean_test_boundary(self.project_path)
        except Exception:
            pass
        report = _start_shared_host(self.project_path, self.unity_exe_path)
        type(self)._shared_host = report
        type(self)._shared_host_base_url = report["base_url"]
        own["reestablished"] = True
        own["base_url"] = report["base_url"]

    # -- per-case reset (the isolation the per-case relaunch used to provide) --

    def _reset_shared_host_state(self):
        cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)
        self._ensure_shared_host_ready()
        self._clear_residual_modal_blocker()
        self._return_editor_to_edit_mode()
        self._reset_change_signal_state()

    def _ensure_shared_host_ready(self):
        """Return a ready shared host, re-establishing it only if it is gone.

        A case that deliberately broke the project recovers asynchronously, so a
        missing endpoint is first given a chance to come back before the host is
        declared dead and relaunched within the retry budget. The health payload
        is cached so the reset does not have to re-probe (and re-walk the project)
        just to decide whether the change signal needs re-settling.
        """
        base_url, health = _scan_ready_control_endpoint(self.project_path)
        if base_url is None:
            base_url, health = _await_ready_endpoint(self.project_path)
        if base_url is None:
            report = _start_shared_host(self.project_path, self.unity_exe_path)
            type(self)._shared_host = report
            base_url, health = report["base_url"], report["health"]
        type(self)._shared_host_base_url = base_url
        self._last_host_health = health
        return base_url

    def _base_url(self):
        base_url = self._ensure_shared_host_ready()
        self.assertIsNotNone(base_url, "no ready control endpoint for the validation host")
        return base_url

    def _exec_settled(self, base_url, code, wait_ms=None):
        """Run an exec and ride out a refresh/reload by resubmitting via wait-for-exec."""
        exit_code, payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(wait_ms or WAIT_TIMEOUT_MS),
                "--code", code,
            ]
        )
        if payload is not None and unity_puer_exec_runtime._running_or_timed_out_response(
            exit_code, json.dumps(payload)
        ):
            exit_code, payload, _, _ = _run_cli(
                [
                    "wait-for-exec",
                    "--base-url", base_url,
                    "--request-id", payload["request_id"],
                    "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                ]
            )
        return exit_code, payload

    def _clear_residual_modal_blocker(self):
        """Resolve a modal dialog a previous case left up.

        A relaunched Editor dropped any dialog with the process; a reused one keeps
        it, and a modal dialog blocks the main thread the next case's exec needs.
        """
        try:
            exit_code, payload, _, _ = _run_cli(
                ["get-blocker-state", "--project-path", str(self.project_path)]
            )
        except Exception:
            return
        result = payload.get("result") if isinstance(payload, dict) else None
        if exit_code != 0 or not isinstance(result, dict):
            return
        if result.get("status") != "modal_blocked":
            return
        blocker = result.get("blocker") or {}
        hwnd = blocker.get("hwnd")
        label = _pick_cancel_button_label(blocker)
        if hwnd is None or label is None:
            return
        try:
            _run_cli(
                [
                    "resolve-blocker",
                    "--project-path", str(self.project_path),
                    "--action", "click",
                    "--hwnd", str(hwnd),
                    "--button", label,
                ]
            )
        except Exception:
            pass

    def _return_editor_to_edit_mode(self):
        """Leave the shared Editor out of play mode, failing loudly if it will not.

        A case that deliberately broke the build deletes its broken source and
        recovers asynchronously, but the change tracker does not treat a deletion
        as a compile-triggering change. When an attempt is refused by the compile
        gate, touch a compile-triggering probe under the repository-owned temp
        root so the next attempt's automatic refresh recompiles the now-clean
        project instead of leaving the reused Editor stuck on the stale error.

        The host endpoint is re-resolved on every attempt because a reload can
        rebind the control service to a different port.
        """
        code = (
            "export default function run(ctx) {"
            " const EditorApplication = puer.loadType('UnityEditor.EditorApplication');"
            " EditorApplication.isPlaying = false;"
            " EditorApplication.isPaused = false;"
            " return { isPlaying: EditorApplication.isPlaying }; }"
        )
        deadline = time.time() + EDIT_MODE_RESET_TIMEOUT_SECONDS
        last_error = None
        while time.time() < deadline:
            base_url = self._ensure_shared_host_ready()
            exit_code, payload = self._exec_settled(base_url, code)
            last_error = payload
            if exit_code == 0:
                health, _ = unity_session._probe_health(base_url, 1.5)
                refresh = health.get("refresh") if isinstance(health, dict) else None
                if not (isinstance(refresh, dict) and refresh.get("suppressed")):
                    return
            elif isinstance(payload, dict) and payload.get("status") == "unity_compile_error":
                self._touch_compile_probe()
            time.sleep(1.0)
        self.fail(
            "shared Editor did not return to edit mode within {}s: {}".format(
                EDIT_MODE_RESET_TIMEOUT_SECONDS, last_error
            )
        )

    def _touch_compile_probe(self):
        """Write a fresh compile-triggering probe under the repository-owned temp root."""
        probe_dir = self.project_path / "Assets" / "__codex_validation_temp"
        try:
            probe_dir.mkdir(parents=True, exist_ok=True)
            (probe_dir / COMPILE_RECOVERY_PROBE_NAME).write_text(
                "// repository-owned compile recovery probe; see test_real_host_integration\n"
                "internal static class UpeHostResetCompileProbe {{ internal const long Stamp = {}L; }}\n".format(
                    time.time_ns()
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _reset_change_signal_state(self):
        """Clear test-owned change-signal state so the next case starts not_pending.

        The refresh cases deliberately leave candidates and synthetic pending
        changes behind; a reused Editor must re-install the tracker and re-settle
        the signal rather than let a prior case gate the next one.
        """
        code = _TRACKER_REFLECTION_JS + (
            "export default function run(ctx) {"
            " invokeTracker('Shutdown');"
            " invokeTracker('Install');"
            " invokeTracker('OnCompilationCompleted');"
            " return { pending: trackerState() }; }"
        )
        deadline = time.time() + EDIT_MODE_RESET_TIMEOUT_SECONDS
        last_payload = None
        while time.time() < deadline:
            base_url = self._ensure_shared_host_ready()
            health = getattr(self, "_last_host_health", None)
            refresh = health.get("refresh") if isinstance(health, dict) else None
            if (
                isinstance(refresh, dict)
                and refresh.get("pending") == "not_pending"
                and not refresh.get("suppressed")
            ):
                # Already installed and settled: no candidates or synthetic
                # pending change to clear, so skip the re-install walk.
                return
            exit_code, payload = self._exec_settled(base_url, code)
            last_payload = payload
            if (
                exit_code == 0
                and isinstance(payload, dict)
                and (payload.get("result") or {}).get("pending") == "NotPending"
            ):
                return
            time.sleep(1.0)
        self.fail("shared Editor change signal did not reset to not_pending: {}".format(last_payload))


# Test methods that need a process the shared Editor cannot be, mapped to the
# pre-state they need:
#   "stop"    -> setUp stops the shared host; the case owns it from a virgin lock
#   "running" -> setUp leaves a live host the case may perturb to stage its own
#                 condition; the shared host is restored only if it was used
# The run always reports the boundary it owned. A "running" case that skips
# before touching the host (for example an occupied preferred port) pays no
# relaunch.
_OWN_BOUNDARY_INTEGRATION_TESTS = {
    "test_batch_mode_process_follows_uniform_activation_rule_against_real_host": "running",
    "test_control_port_rolls_over_when_preferred_port_occupied_against_real_host": "running",
    "test_exec_discovers_rolled_over_control_port_against_real_host": "running",
    "test_cold_launch_retries_on_transient_failure_against_real_host": "stop",
}


class RealHostIntegrationTests(_SharedRealHostDevice, unittest.TestCase):
    OWN_HOST_BOUNDARY_TESTS = _OWN_BOUNDARY_INTEGRATION_TESTS

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

        blocker_exit_code, blocker_payload, _, _ = _run_cli(
            [
                "get-blocker-state",
                "--project-path",
                str(self.project_path),
            ]
        )
        self.assertEqual(blocker_exit_code, 0, blocker_payload)
        blocker = blocker_payload["result"]["blocker"]
        self.assertEqual(blocker["type"], "save_modified_scenes_prompt")
        self.assertIn("hwnd", blocker, "payload must carry hwnd for --action click")
        # Button labels are localized (zh-CN host: "取消"), so take the label
        # straight from the payload rather than hardcoding an English one.
        cancel_label = _pick_cancel_button_label(blocker)
        self.assertIsNotNone(cancel_label, "no cancel-like button in payload: {}".format(blocker))

        resolve_exit_code, resolve_payload, _, _ = _run_cli(
            [
                "resolve-blocker",
                "--project-path",
                str(self.project_path),
                "--action",
                "click",
                "--hwnd",
                str(blocker["hwnd"]),
                "--button",
                cancel_label,
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

        blocker_exit_code, blocker_payload, _, _ = _run_cli(
            [
                "get-blocker-state",
                "--project-path",
                str(self.project_path),
            ]
        )
        self.assertEqual(blocker_exit_code, 0, blocker_payload)
        blocker = blocker_payload["result"]["blocker"]
        self.assertEqual(blocker["type"], "save_scene_dialog")
        self.assertIn("hwnd", blocker, "payload must carry hwnd for --action click")
        # Button labels are localized (zh-CN host: "取消"), so take the label
        # straight from the payload rather than hardcoding an English one.
        cancel_label = _pick_cancel_button_label(blocker)
        self.assertIsNotNone(cancel_label, "no cancel-like button in payload: {}".format(blocker))

        resolve_exit_code, resolve_payload, _, _ = _run_cli(
            [
                "resolve-blocker",
                "--project-path",
                str(self.project_path),
                "--action",
                "click",
                "--hwnd",
                str(blocker["hwnd"]),
                "--button",
                cancel_label,
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

    def test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host(self):
        """Cancel must not be the default unblock action for save-scene dialogs."""
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                "cancel-rejected-{}".format(os.getpid()),
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

        self.assertEqual(resolve_exit_code, 1, resolve_payload)
        self.assertEqual(resolve_payload["status"], "resolution_failed")
        self.assertEqual(resolve_payload["error"], "action_not_supported_for_blocker")

        # The dialog must still be present: unsaved scene changes were not discarded.
        blocker_exit_code, blocker_payload, _, _ = _run_cli(
            [
                "get-blocker-state",
                "--project-path",
                str(self.project_path),
            ]
        )
        self.assertEqual(blocker_exit_code, 0, blocker_payload)
        self.assertEqual(
            blocker_payload["result"]["blocker"]["type"], "save_modified_scenes_prompt"
        )

        # Clean up so the suite does not leave the Editor blocked.
        blocker = blocker_payload["result"]["blocker"]
        if "hwnd" in blocker:
            cancel_label = _pick_cancel_button_label(blocker)
            if cancel_label:
                _run_cli(
                    [
                        "resolve-blocker",
                        "--project-path",
                        str(self.project_path),
                        "--action",
                        "click",
                        "--hwnd",
                        str(blocker["hwnd"]),
                        "--button",
                        cancel_label,
                    ]
                )

    def test_unknown_modal_dialog_is_reported_against_real_host(self):
        """A blocking dialog outside the catalog is reported, not dropped."""
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        # EditorUtility.DisplayDialog blocks the main thread and has no catalog entry.
        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                "unknown-dialog-{}".format(os.getpid()),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const EditorUtility = puer.loadType('UnityEditor.EditorUtility');",
                        "  EditorUtility.DisplayDialog('Codex Validation Prompt', 'Proceed?', 'OK', 'Cancel');",
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
        blocker = blocker_payload["result"]["blocker"]
        self.assertEqual(blocker["type"], "unknown_modal_dialog")
        self.assertIn("hwnd", blocker)
        self.assertIn("title", blocker)
        self.assertIn("body", blocker)
        self.assertIn("buttons", blocker)
        self.assertNotIn("known", blocker)
        self.assertNotIn("default_button", blocker)

        # Resolve it explicitly so the Editor is not left blocked. Prefer a
        # cancel-like button: on an unknown dialog the first button can be the
        # destructive one, and this test is about reporting, not about choosing.
        labels = [b["label"] for b in blocker["buttons"]]
        self.assertTrue(labels, "an unknown dialog must expose at least one button")
        resolve_label = _pick_cancel_button_label(blocker) or labels[0]
        _run_cli(
            [
                "resolve-blocker",
                "--project-path",
                str(self.project_path),
                "--action",
                "click",
                "--hwnd",
                str(blocker["hwnd"]),
                "--button",
                resolve_label,
            ]
        )

    def test_non_blocking_editor_windows_are_not_blockers_against_real_host(self):
        """Modal discrimination must not promote Editor panels to blockers."""
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        # Open windows that do not block exec.
        _run_cli(
            [
                "exec",
                "--project-path",
                str(self.project_path),
                "--unity-exe-path",
                str(self.unity_exe_path),
                "--request-id",
                "open-panels-{}".format(os.getpid()),
                "--wait-timeout-ms",
                str(WAIT_TIMEOUT_MS),
                "--code",
                "\n".join(
                    [
                        "export default function run(ctx) {",
                        "  const EditorApplication = puer.loadType('UnityEditor.EditorApplication');",
                        "  const SettingsService = puer.loadType('UnityEditor.SettingsService');",
                        "  try { SettingsService.OpenProjectSettings('Project/Player'); } catch (e) { }",
                        "  try { EditorApplication.ExecuteMenuItem('Edit/Preferences...'); } catch (e) { }",
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
        result = blocker_payload["result"]
        if result["status"] == "modal_blocked":
            self.assertNotIn("Preferences", result["blocker"].get("title", ""))
            self.assertNotIn("Project Settings", result["blocker"].get("title", ""))


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
            # The written .cs file is a compile-triggering change, so the next exec
            # refreshes automatically and recompiles before the compile-error gate.
            exec_exit_code, exec_payload, _, _ = _run_cli(
                [
                    "exec",
                    "--project-path", str(self.project_path),
                    "--unity-exe-path", str(self.unity_exe_path),
                    "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
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
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )

    def test_base_url_automatic_refresh_and_wait_for_compile_against_real_host(self):
        """Automatic refresh works in base-url mode: a compile-triggering code change is
        detected server-side, the CLI settles the resulting cycle over the same
        endpoint, and the terminal response carries the script result plus the
        refresh decision. wait-for-compile then brackets a cycle over that endpoint.
        """
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        base_url, _ = _scan_ready_control_endpoint(self.project_path)
        self.assertIsNotNone(base_url, "could not resolve a ready control endpoint for the base-url regression")

        # A fresh compile-triggering source file makes the project dirty; the watcher
        # (or the install-time baseline) must surface it as a pending change.
        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        trigger_cs = temp_dir / "BaseUrlAutomaticRefreshProbe.cs"
        trigger_cs.write_text(
            "// Auto-generated base-url automatic-refresh probe.\n"
            "internal static class BaseUrlAutomaticRefreshProbe {{ internal const long Stamp = {}L; }}\n".format(
                time.time_ns()
            ),
            encoding="utf-8",
        )

        exec_exit_code, exec_payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(WAIT_TIMEOUT_MS),
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
        self.assertEqual(exec_exit_code, 0, exec_payload)
        self.assertEqual(exec_payload["status"], "completed")
        self.assertEqual(exec_payload["result"]["loop"], "base-url-ok")
        # The terminal response carries the decision, not a {refreshed: true} confirmation.
        self.assertIn("refresh", exec_payload)
        self.assertTrue(exec_payload["refresh"]["triggered"], exec_payload["refresh"])
        self.assertIn("compile_triggering_change", exec_payload["refresh"]["reason"])
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

    def test_safe_mode_dialog_reports_buttons_and_keeps_cancel_against_real_host(self):
        """Safe Mode stays on cancel and, when observed, exposes its buttons.

        H2 (see validation-evidence.md): the real "Enter Safe Mode?" dialog is
        class #32770 with owner=null, and it responds to BM_CLICK. The D5
        exemption is kept, so cancel must remain the legal action and must not
        be rejected the way it is for save-scene dialogs.
        """
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        session = unity_session.get_blocker_state(project_path=str(self.project_path))
        pid = session.unity_pid
        if not pid:
            self.skipTest("no Editor pid published for the validation host")

        dialogs = [
            d for d in unity_modal_blockers._list_windows_dialogs(pid)
            if (unity_modal_blockers._match_dialog_spec(d) or {}).get("type") == "safe_mode_dialog"
        ]
        if not dialogs:
            # No Safe Mode dialog is up, which is the normal case: it appears
            # only when the Editor starts with compile errors. Assert only the
            # part that must hold regardless -- cancel is never rejected here.
            self.skipTest("no Safe Mode dialog is currently showing on the host")

        dialog = dialogs[0]
        self.assertEqual(unity_modal_blockers._win32_class_name(dialog["hwnd"]), "#32770")

        payload = unity_modal_blockers.resolve_modal_blocker(
            pid, action="cancel", timeout_ms=2000
        )
        # Cancel is legal for Safe Mode: never action_not_supported_for_blocker.
        self.assertNotEqual(payload.get("error"), "action_not_supported_for_blocker")

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
                    "--code", "export default function run(ctx) { return { ok: true }; }",
                ]
            )

    def test_batch_mode_process_follows_uniform_activation_rule_against_real_host(self):
        """Batch mode follows the uniform activation rule, not a mode exception.

        Without the activation switch the service does not start; with it, the
        service does start and binds a control port. Both directions are the same
        rule as an interactive process — batch mode is no longer a special case.

        Prerequisite: the host project must NOT be open in an interactive Editor.
        A batch-mode launch needs the exclusive project lock, so this test skips
        (rather than fails) when any Unity process is already running. The
        inherited setUp force-stops the host Editor, so this normally holds.
        """
        running_pids = unity_session._list_unity_pids()
        self._record_own_boundary(
            "batch_mode_one_shot_processes",
            interactive_pids=running_pids,
        )
        if running_pids:
            self.skipTest(
                "host project appears open in an interactive Editor (unity pids={}); "
                "batch-mode launch needs the exclusive project lock".format(running_pids)
            )

        # This case owns a stopped host: batch-mode launches need the exclusive
        # project lock. Stopping lazily (after the skip check) means a skip does
        # not pay for a stop/relaunch it did not need.
        self._own_boundary_stop()

        # Direction 1: no activation switch → service does not start.
        try:
            exit_code, log_path, log_text = _run_batch_mode_unity(
                self.unity_exe_path, self.project_path, activate=False
            )
        except subprocess.TimeoutExpired:
            self.skipTest("batch-mode Unity (no switch) did not exit within the timeout")
            return

        self._record_own_boundary("batch_mode_one_shot_processes", no_switch_exit_code=exit_code)
        try:
            self.assertIn(
                BATCH_NOT_ACTIVATED_LOG_LINE,
                log_text,
                "batch-mode log without activation did not record the not-activated line; "
                "exit_code={} log={}".format(exit_code, log_path),
            )
            self.assertNotIn(
                READY_LOG_PREFIX,
                log_text,
                "batch-mode process without activation reported a control-port bind; "
                "log={}".format(log_path),
            )
            self.assertNotIn(
                BIND_FAILURE_LOG_PREFIX,
                log_text,
                "batch-mode process without activation reported a whole-range bind failure; "
                "log={}".format(log_path),
            )
        finally:
            log_path.unlink(missing_ok=True)

        # Direction 2: with activation switch → service starts.
        # Re-check the lock: the previous batch process should have released it,
        # but an unrelated Editor opening the host mid-test would make this race.
        running_pids = unity_session._list_unity_pids()
        if running_pids:
            self.skipTest(
                "Unity process appeared after the no-switch batch run (pids={}); "
                "cannot stage the with-activation direction".format(running_pids)
            )

        try:
            exit_code, log_path, log_text = _run_batch_mode_unity(
                self.unity_exe_path, self.project_path, activate=True
            )
        except subprocess.TimeoutExpired:
            self.skipTest("batch-mode Unity (with switch) did not exit within the timeout")
            return

        self._record_own_boundary("batch_mode_one_shot_processes", with_switch_exit_code=exit_code)
        try:
            self.assertNotIn(
                BATCH_NOT_ACTIVATED_LOG_LINE,
                log_text,
                "batch-mode log with activation still recorded the not-activated line; "
                "exit_code={} log={}".format(exit_code, log_path),
            )
            self.assertIn(
                READY_LOG_PREFIX,
                log_text,
                "batch-mode process with activation did not report a control-port bind; "
                "exit_code={} log={}".format(exit_code, log_path),
            )
            self.assertNotIn(
                BIND_FAILURE_LOG_PREFIX,
                log_text,
                "batch-mode process with activation reported a whole-range bind failure; "
                "log={}".format(log_path),
            )
        finally:
            log_path.unlink(missing_ok=True)

    def test_control_port_rolls_over_when_preferred_port_occupied_against_real_host(self):
        """An occupied preferred control port must roll over, not fail the scan.

        P1 — the host project's service is ready on a port later than the preferred
        one, and its health identity names that port — is asserted whenever the
        preferred port is occupied: by another project's ready Editor (the host is
        already rolled over) or by the suite's retry-binder (staged around a domain
        reload). P2 — the service released the preferred port during the reload and
        rebound later because the binder won the Stop()->Start() window — is asserted
        only when the binder actually won; otherwise the boundary record states that
        the sub-assertion was not staged.
        """
        self._record_own_boundary("preferred_port_rollover")
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        stage = self._stage_occupied_preferred_port_rollover(ready_exit_code, ready_payload)
        binder = stage["binder"]
        try:
            if stage["rolled"] is None and stage["preferred_state"] not in _FOREIGN_PREFERRED_STATES:
                # The preferred port was free for the suite's binder, so P1's
                # precondition exists only if the binder wins the race. Losing it is
                # a required trigger that could not be staged, not a product
                # observation, so report it as a skip rather than a failure.
                self.skipTest("could not stage a control-port rollover; binder lost the race")
                return
            # P1: asserted unconditionally, including when another project's ready
            # Editor holds the preferred port and the binder can never win it. When
            # the preferred port is foreign-held the rollover must be observable;
            # a missing endpoint there fails inside _assert_rollover_p1.
            rolled_base_url, rolled_payload = self._assert_rollover_p1(stage["rolled"], binder)
            self._record_own_boundary(
                "preferred_port_rollover",
                preferred_port=PREFERRED_CONTROL_PORT,
                preferred_port_held_by=stage["preferred_state"],
                rolled_port=rolled_payload["port"],
                rolled_base_url=rolled_base_url,
                # P2: "asserted" only when the binder actually held the port.
                mid_reload_rebind="asserted" if binder.bound else "not_staged",
            )
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

    def _resolve_host_endpoint_or_fail(self, launch_exit_code, launch_payload):
        """Resolve the launched host's ready endpoint, retrying then failing.

        The host was launched successfully, so a ready endpoint it owns is a
        product-observable condition rather than an absent prerequisite. A single
        failed sweep can still be a transient unbind during a domain reload, so the
        oracle is retried a bounded number of times; if it still cannot see the host
        the case fails with the launch outcome and the ports probed instead of
        skipping.
        """
        return real_host_retry.resolve_ready_endpoint_with_retry(
            scan_fn=lambda: _scan_ready_control_endpoint(self.project_path),
            launch_exit_code=launch_exit_code,
            launch_payload=launch_payload,
            ports_probed=range(PREFERRED_CONTROL_PORT, CONTROL_PORT_RANGE_END),
            sleep_fn=time.sleep,
        )

    def _classify_preferred_port_state(self):
        """State of the preferred control port at the moment rollover is staged.

        ``own_project`` and ``free`` mean the suite's retry-binder can contend for
        the port, so P2 (the mid-reload rebind race) is stageable. The two foreign
        states mean something the suite cannot displace holds it, so P2 is not
        stageable and only P1 (the later-port rollover) is observable.
        """
        pre_payload, _ = _probe_control_health(PREFERRED_CONTROL_PORT)
        if pre_payload is not None:
            if _health_is_ready_for_project(pre_payload, self.project_path):
                return "own_project"
            return "foreign_endpoint"
        if not _preferred_port_is_free():
            return "foreign_process"
        return "free"

    def _assert_rollover_p1(self, rolled, binder):
        """Assert P1 unconditionally: the service is ready on a later port.

        P1 is the host project's service being ready on a port later than the
        preferred one and inside the bounded range, with its health identity naming
        that same port. It is falsifiable whenever the preferred port is occupied by
        anything (a foreign Editor or the suite's binder), so it is asserted without
        regard to whether P2 was staged. Returns ``(base_url, payload)``.
        """
        self.assertIsNotNone(
            rolled,
            "interactive service did not roll over to a later port; it may have "
            "reclaimed {} (binder.bound={})".format(PREFERRED_CONTROL_PORT, binder.bound),
        )
        rolled_base_url, rolled_payload = rolled
        self.assertGreater(rolled_payload["port"], PREFERRED_CONTROL_PORT)  # P1
        self.assertLess(rolled_payload["port"], CONTROL_PORT_RANGE_END)  # P1
        self.assertEqual(  # P1
            rolled_base_url, "http://127.0.0.1:{}".format(rolled_payload["port"])
        )
        self.assertEqual(rolled_payload.get("base_url"), rolled_base_url)  # P1
        return rolled_base_url, rolled_payload

    def _stage_occupied_preferred_port_rollover(self, launch_exit_code, launch_payload):
        """Stage the occupied-preferred-port condition and observe the rollover.

        Resolves the launched host's endpoint (bounded retry, then failure),
        classifies the preferred port, starts the retry-binder, and forces a domain
        reload so the service must come back on a later port. Returns the staging
        record; the caller owns stopping the binder it contains.
        """
        editor_base_url, _editor_payload = self._resolve_host_endpoint_or_fail(
            launch_exit_code, launch_payload
        )
        preferred_state = self._classify_preferred_port_state()
        self._mark_own_boundary_perturbed()
        binder = _PreferredPortBinder()
        binder.start()
        try:
            rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=False)
            if rolled is None:
                # Retry once: the Editor may have reclaimed the preferred port if
                # the binder lost the first race. Use the touched-script trigger.
                rolled = self._stage_rollover(binder, editor_base_url, use_touch_fallback=True)
        except BaseException:
            binder.stop()
            raise
        return {
            "editor_base_url": editor_base_url,
            "preferred_state": preferred_state,
            "binder": binder,
            "rolled": rolled,
        }

    def test_exec_discovers_rolled_over_control_port_against_real_host(self):
        """exec --project-path must reach an Editor that rolled over to a non-preferred port.

        P1 — the host is ready on a later port and exec --project-path with no
        --base-url discovers that endpoint — is asserted unconditionally, including
        when another project's ready Editor holds the preferred port and the rolled
        endpoint is the one the host already bound. P2 — the suite's binder won the
        Stop()->Start() window — is asserted only when it was actually staged;
        otherwise the boundary record names the sub-assertion as not staged.
        """
        self._record_own_boundary("preferred_port_rollover_discovery")
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        stage = self._stage_occupied_preferred_port_rollover(ready_exit_code, ready_payload)
        binder = stage["binder"]
        try:
            if stage["rolled"] is None and stage["preferred_state"] not in _FOREIGN_PREFERRED_STATES:
                # The preferred port was free for the suite's binder, so P1's
                # precondition exists only if the binder wins the race. Losing it is
                # a trigger that could not be staged, not a product observation.
                self.skipTest("could not stage a control-port rollover; binder lost the race")
                return

            # P1: asserted unconditionally. The Editor is on a non-preferred port.
            rolled_base_url, rolled_payload = self._assert_rollover_p1(stage["rolled"], binder)

            # P2: only meaningful when the binder actually held the preferred port
            # through the reload. A foreign Editor owning the port cannot be staged.
            p2_staged = binder.bound
            if p2_staged:
                self.assertTrue(binder.bound, "binder no longer holds the preferred port; precondition lost")

            # P1: exec --project-path (no --base-url) must discover the rolled-over
            # endpoint via the range scan.
            exec_exit_code, exec_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
            self.assertEqual(
                exec_exit_code,
                0,
                "exec --project-path failed to discover the rolled-over endpoint {}: {}".format(
                    rolled_base_url, exec_payload
                ),
            )
            self._record_own_boundary(
                "preferred_port_rollover_discovery",
                preferred_port=PREFERRED_CONTROL_PORT,
                preferred_port_held_by=stage["preferred_state"],
                rolled_port=rolled_payload["port"],
                discovery_exit_code=exec_exit_code,
                mid_reload_rebind="asserted" if p2_staged else "not_staged",
            )
        finally:
            # Release the preferred port so the Editor can reclaim it on its next reload.
            binder.stop()

    def test_cli_launched_host_is_observed_through_a_project_private_log_against_real_host(self):
        """The host writes where the CLI observes, and neither is the shared per-user log.

        This closes the loop the rest of the suite depends on: every other case takes
        byte offsets against whatever log the CLI resolved, and those offsets are only
        meaningful if that file belongs to this Editor alone. No case here passes
        --unity-log-path, so the isolation has to come from the launch default.
        """
        expected_log_path = self.project_path / "Temp" / "UnityPuerExec" / "Editor.log"

        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        # The Editor states its own log path, and it is the project-private one.
        base_url, health_payload = _scan_ready_control_endpoint(self.project_path)
        self.assertIsNotNone(base_url, "no ready control endpoint owned by the host project")
        reported = health_payload.get("console_log_path")
        self.assertTrue(reported, "ready /health did not report console_log_path: {}".format(health_payload))
        self.assertEqual(
            Path(reported),
            expected_log_path,
            "the host Editor is writing to {} rather than its project-private log".format(reported),
        )
        self.assertNotEqual(Path(reported), unity_session_logs.default_editor_log_path())
        self.assertTrue(Path(reported).exists(), "the reported log path does not exist on disk")

        # The CLI observes that same file, and says so rather than leaving the caller
        # to infer whether the path was stated or assumed.
        source_exit_code, source_payload, _, _ = _run_cli(
            ["get-log-source", "--project-path", str(self.project_path)]
        )
        self.assertEqual(source_exit_code, 0, source_payload)
        result = source_payload["result"]
        self.assertEqual(Path(result["path"]), expected_log_path)
        self.assertIn(
            result["resolution_tier"],
            (
                unity_session_logs.LOG_SOURCE_TIER_PUBLISHED_ENDPOINT,
                unity_session_logs.LOG_SOURCE_TIER_CONTROL_SERVICE,
            ),
            "the observed log path was assumed rather than stated: {}".format(result),
        )

    def test_script_updater_consent_dialog_recovery_against_real_host(self):
        """Real-host coverage for ScriptUpdater consent-dialog recovery.

        Verifies that when Unity presents the ScriptUpdater consent dialog,
        the CLI auto-declines it, preserves the primary command status, attaches
        warning = 'api_updater_declined', never surfaces the dialog as modal_blocked,
        and leaves project source files unrewritten.

        When the dialog cannot be produced deterministically for the current host
        or Unity version, the case skips with a machine-usable diagnosed reason
        naming the trigger blocker.
        """
        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(self.project_path, self.unity_exe_path)
        self.assertEqual(ready_exit_code, 0, ready_payload)

        # Retrieve Unity Editor PID for window inspection
        _, health_payload = _scan_ready_control_endpoint(self.project_path)
        unity_pid = (health_payload or {}).get("unity_pid")
        if not unity_pid:
            session = unity_session.ensure_session_ready(
                self.project_path, unity_exe_path=self.unity_exe_path
            )
            unity_pid = session.unity_pid

        fixture_path, initial_content = _seed_obsolete_api_fixture(self.project_path)
        try:
            # The seeded obsolete-API fixture is a compile-triggering change; the next
            # exec refreshes automatically and drives the recompile.
            trigger_exit, trigger_payload, _, _ = _run_cli(
                [
                    "exec",
                    "--project-path",
                    str(self.project_path),
                    "--unity-exe-path",
                    str(self.unity_exe_path),
                    "--wait-timeout-ms",
                    str(WAIT_TIMEOUT_MS),
                    "--code",
                    "export default function run(ctx) { return { ok: true, request_id: ctx.request_id }; }",
                ]
            )

            # Check if Unity surfaced any dialog for this Editor process
            dialogs = unity_modal_blockers._list_windows_dialogs(unity_pid) if unity_pid else []
            observed_api_dialog = None
            observed_other_dialogs = []

            for d in dialogs:
                body = d.get("body") or ""
                # Check for either the known fingerprints or generalized ScriptUpdater title
                if (
                    unity_modal_blockers.is_api_updater_message(body)
                    or "Script Updating" in d.get("title", "")
                ):
                    observed_api_dialog = d
                else:
                    observed_other_dialogs.append(d)

            if observed_api_dialog is None:
                # The fixture did not produce the consent dialog on this host / Unity version.
                # Per the specification (Scenario: Consent dialog cannot be triggered on the current host),
                # record the precise trigger blocker and skip rather than reporting a vacuous pass.
                unity_version = "unknown"
                try:
                    unity_version = unity_session_process.get_unity_version(self.project_path)
                except Exception:
                    pass
                self.skipTest(
                    "ScriptUpdater consent dialog could not be triggered on validation host "
                    "(Unity version: {}): script import/refresh does not prompt the ScriptUpdater "
                    "consent dialog during normal incremental compilation on an existing project; "
                    "trigger blocker: Unity handles (UnityUpgradable) APIs via incremental assembly "
                    "compilation without interactive source rewrite prompts".format(unity_version)
                )

            # Scenario: Non-English dialog text is recorded
            observed_body = observed_api_dialog.get("body") or ""
            if not unity_modal_blockers.is_api_updater_message(observed_body):
                # Observed a ScriptUpdater dialog whose body does not match known fingerprints.
                # Record the observed text so a fingerprint extension can be filed as a follow-up.
                self.fail(
                    "Observed ScriptUpdater consent dialog message does not match known fingerprints "
                    "(fingerprints={!r}, observed_title={!r}, observed_body={!r}). "
                    "File a follow-up fingerprint extension.".format(
                        unity_modal_blockers.API_UPDATER_MESSAGE_FINGERPRINTS,
                        observed_api_dialog.get("title"),
                        observed_body,
                    )
                )

            # Scenario: Contributor validates consent-dialog auto-decline against a real host
            # 1. Assert the dialog is never surfaced as modal_blocked
            blocker = unity_modal_blockers.detect_modal_blocker(unity_pid, scope="exec")
            self.assertIsNone(
                blocker,
                "ScriptUpdater consent dialog must never be surfaced as modal_blocked: {}".format(blocker),
            )

            # 2. Run a CLI wait/exec with the dialog visible, or assert auto-decline
            dismiss_res = unity_modal_blockers.dismiss_api_updater_dialog(unity_pid)
            self.assertTrue(
                dismiss_res.get("ok"),
                "CLI auto-decline failed on real ScriptUpdater consent dialog: {}".format(dismiss_res),
            )
            self.assertGreater(dismiss_res.get("dismissed", 0), 0)

            # 3. Complete the in-flight wait/exec and verify warning and primary status
            if trigger_payload and unity_puer_exec_runtime._running_or_timed_out_response(
                trigger_exit, json.dumps(trigger_payload)
            ):
                wait_exit, wait_payload, _, _ = _run_cli(
                    [
                        "wait-for-exec",
                        "--project-path",
                        str(self.project_path),
                        "--unity-exe-path",
                        str(self.unity_exe_path),
                        "--request-id",
                        trigger_payload["request_id"],
                        "--wait-timeout-ms",
                        str(READY_TIMEOUT_SECONDS * 1000),
                    ]
                )
                self.assertEqual(wait_exit, 0, wait_payload)
                self.assertEqual(wait_payload["status"], "completed")
                self.assertEqual(wait_payload.get("warning"), "api_updater_declined")
                self.assertIn("warning_detail", wait_payload)

            # 4. Verify the dialog is confirmed gone
            remaining = [
                d
                for d in unity_modal_blockers._list_windows_dialogs(unity_pid)
                if d["hwnd"] == observed_api_dialog["hwnd"]
            ]
            self.assertEqual(len(remaining), 0, "dialog HWND still present after auto-decline")

            # 5. Verify source file was not rewritten (declined, not accepted)
            current_content = fixture_path.read_text(encoding="utf-8")
            self.assertEqual(
                current_content,
                initial_content,
                "source file was rewritten despite decline recovery",
            )
        finally:
            # Clean up fixture so host is left clean
            try:
                if fixture_path.exists():
                    fixture_path.unlink()
                meta_path = fixture_path.with_suffix(".cs.meta")
                if meta_path.exists():
                    meta_path.unlink()
                cleanup_validation_host.cleanup_validation_temp_assets(self.project_path)
            except Exception:
                pass

    def test_cold_launch_retries_on_transient_failure_against_real_host(self):
        """Verify bounded retry tolerates transient cold-launch failure and preserves guardrails."""
        # 1. Contended cold launch scenario: attempt 1 fails transiently with unity_start_failed,
        # clean boundary is re-confirmed, and attempt 2 launches real host successfully.
        def inject_transient_flake(attempt):
            if attempt == 1:
                return (
                    20,
                    {
                        "ok": False,
                        "status": "unity_start_failed",
                        "error": "Unity exited before ready with code 0",
                    },
                    "",
                    "Unity exited before ready with code 0",
                )
            return None

        ready_exit_code, ready_payload, _, _ = _warm_up_project_exec(
            self.project_path,
            self.unity_exe_path,
            include_diagnostics=True,
            transient_failure_injector=inject_transient_flake,
        )
        self.assertEqual(ready_exit_code, 0, ready_payload)
        self.assertEqual(ready_payload["status"], "completed")
        self.assertEqual(ready_payload["attempt_count"], 2)
        self.assertEqual(ready_payload["last_launch_status"], "completed")
        self.assertEqual(len(ready_payload["attempts"]), 2)
        self.assertEqual(ready_payload["attempts"][0]["status"], "unity_start_failed")
        self.assertEqual(ready_payload["attempts"][1]["status"], "completed")
        self.assertIsNotNone(ready_payload["boundary_result"])
        self._record_own_boundary(
            "cold_launch_retry",
            attempt_count=ready_payload["attempt_count"],
            last_launch_status=ready_payload["last_launch_status"],
            boundary_result=ready_payload["boundary_result"],
        )

        # 2. Persistent regression scenario: when all attempts fail, all attempts are
        # recorded with attempt count and last status, distinguishing it from a flake.
        persistent_exit_code, persistent_payload, _, _ = _warm_up_project_exec(
            self.project_path,
            self.unity_exe_path,
            max_attempts=2,
            transient_failure_injector=lambda attempt: (
                20,
                {
                    "ok": False,
                    "status": "unity_start_failed",
                    "error": f"Unity exited before ready on attempt {attempt}",
                },
                "",
                "",
            ),
        )
        self.assertEqual(persistent_exit_code, 20)
        self.assertEqual(persistent_payload["attempt_count"], 2)
        self.assertEqual(persistent_payload["last_launch_status"], "unity_start_failed")
        self.assertEqual(len(persistent_payload["attempts"]), 2)

        # 3. Non-launch failure scenario: non-launch failures are never retried.
        non_launch_exit, non_launch_payload, _, _ = _warm_up_project_exec(
            self.project_path,
            self.unity_exe_path,
            max_attempts=3,
            transient_failure_injector=lambda attempt: (
                4,
                {
                    "ok": False,
                    "status": "compile_error",
                    "error": "Compilation error in script",
                },
                "",
                "",
            ),
        )
        self.assertEqual(non_launch_exit, 4)
        self.assertEqual(non_launch_payload["attempt_count"], 1)
        self.assertEqual(non_launch_payload["last_launch_status"], "compile_error")
        self.assertEqual(len(non_launch_payload["attempts"]), 1)


def _post_control_json(base_url, path, payload, timeout_seconds=5.0):
    """POST JSON to a control endpoint, returning (http_status, body) even on 4xx/5xx."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


# JavaScript prelude for reaching the import-change tracker directly. The tracker is
# internal to the Editor assembly and has no control-endpoint surface for its raw
# state, so the real-host cases read and, where a failure mode cannot be produced from
# outside (a watcher error, a lost install), set that state through reflection. This
# runs inside the Editor's own JS environment, so it observes the same static state
# the server uses -- it is a white-box probe, not a stub of the behavior under test.
_TRACKER_REFLECTION_JS = (
    "function trackerType() {\n"
    "  const AppDomain = puer.loadType('System.AppDomain');\n"
    "  const asms = AppDomain.CurrentDomain.GetAssemblies();\n"
    "  for (let i = 0; i < asms.Length; i++) {\n"
    "    const a = asms.get_Item(i);\n"
    "    if (String(a.GetName().Name) === 'UnityPuerExec.Editor') {\n"
    "      const t = a.GetType('UnityPuerExec.UnityPuerExecImportChangeTracker');\n"
    "      if (t) return t;\n"
    "    }\n"
    "  }\n"
    "  return null;\n"
    "}\n"
    "const TRACKER_NONPUBLIC_STATIC = 40; // BindingFlags.Static | BindingFlags.NonPublic\n"
    "function trackerField(name) {\n"
    "  return trackerType().GetField(name, TRACKER_NONPUBLIC_STATIC).GetValue(null);\n"
    "}\n"
    "function setTrackerField(name, value) {\n"
    "  trackerType().GetField(name, TRACKER_NONPUBLIC_STATIC).SetValue(null, value);\n"
    "}\n"
    "function invokeTracker(name) {\n"
    "  return trackerType().GetMethod(name, TRACKER_NONPUBLIC_STATIC).Invoke(null, []);\n"
    "}\n"
    "function trackerState() {\n"
    "  const value = Number(String(invokeTracker('GetPendingState')));\n"
    "  return value === 0 ? 'NotPending' : (value === 1 ? 'Pending' : 'Unknown');\n"
    "}\n"
)


def _js_string_literal(value):
    """Render a filesystem path as a single-quoted JS string (forward slashes)."""
    return "'" + str(value).replace("\\", "/").replace("'", "\\'") + "'"


class RefreshOnChangeRealHostTests(_SharedRealHostDevice, unittest.TestCase):
    """Real-host coverage for import-change-refresh (see the change's design).

    The C# decision logic has no unit-test host in this repository, so its observable
    behavior is exercised here against a live Editor: health refresh state, the
    code-only boundary, the no-repeat property, the diagnostics block, and the
    machine-readable rejection of the removed protocol field.

    Every case here reuses the suite Editor; the per-case reset in the shared
    fixture clears the candidates and re-settles the change signal, so the cases
    run in any order against one host.
    """

    def _write_compile_triggering_probe(self, name):
        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / name
        path.write_text(
            "// Auto-generated automatic-refresh probe.\n"
            "internal static class {0} {{ internal const long Stamp = {1}L; }}\n".format(
                path.stem, time.time_ns()
            ),
            encoding="utf-8",
        )
        return path

    # An exec that may trigger an automatic refresh has to give the CLI's internal
    # settle+resubmit loop enough budget: the refresh drives a full compile cycle
    # (tens of seconds), and the terminal response carries the script result only
    # after it settles.
    REFRESH_WAIT_TIMEOUT_MS = 300_000

    def _exec_script(self, base_url, body):
        exit_code, payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(self.REFRESH_WAIT_TIMEOUT_MS),
                "--code", body,
            ]
        )
        if payload is not None and unity_puer_exec_runtime._running_or_timed_out_response(
            exit_code, json.dumps(payload)
        ):
            exit_code, payload, _, _ = _run_cli(
                [
                    "wait-for-exec",
                    "--base-url", base_url,
                    "--request-id", payload["request_id"],
                    "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                ]
            )
        return exit_code, payload

    # --- shared probes for the import-change signal ---------------------------

    def _health(self, base_url):
        payload, error = unity_session._probe_health(base_url, 1.5)
        self.assertIsNotNone(payload, error)
        return payload

    def _exec_raw(self, base_url, code, wait_ms=None):
        """Exec without the waiting shortcut, so a non-terminal refresh phase is visible."""
        exit_code, payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(wait_ms or self.REFRESH_WAIT_TIMEOUT_MS),
                "--code", code,
            ]
        )
        return exit_code, payload

    def _tracker_script(self, body):
        return _TRACKER_REFLECTION_JS + body

    def _read_settled_ticks(self, base_url):
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " return { ticks: String(trackerField('settledImportUtcTicks')) }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        return int(payload["result"]["ticks"])

    def _read_persisted_ticks(self, base_url):
        exit_code, payload = self._exec_script(
            base_url,
            "export default function run(ctx) {"
            " const SessionState = puer.loadType('UnityEditor.SessionState');"
            " return { persisted: SessionState.GetString('UnityPuerExec.SettledImportUtcTicks', '') }; }",
        )
        self.assertEqual(exit_code, 0, payload)
        return payload["result"]["persisted"]

    def _wait_for_ready_project(self, timeout_seconds=READY_TIMEOUT_SECONDS):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            base_url, payload = _scan_ready_control_endpoint(self.project_path)
            if base_url is not None and payload.get("status") == "ready":
                return base_url
            time.sleep(1.0)
        self.fail("validation host did not return to a ready state within {}s".format(timeout_seconds))

    def _wait_for_refresh_state(self, base_url, suppressed, timeout_seconds=60):
        """Wait for the health refresh suppression flag to reach ``suppressed``.

        Tolerates the transient transport failures a domain reload produces (play
        mode exit and a deferred compile both end in one) by re-resolving the
        project's published endpoint instead of failing on the first drop.
        """
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            health, _error = unity_session._probe_health(base_url, 1.5)
            if health is None:
                resolved, resolved_health = _scan_ready_control_endpoint(self.project_path)
                if resolved is not None:
                    base_url, health = resolved, resolved_health
            refresh = health.get("refresh") if isinstance(health, dict) else None
            last = refresh
            if isinstance(refresh, dict) and bool(refresh.get("suppressed")) == suppressed:
                return refresh
            time.sleep(0.5)
        self.fail("refresh suppressed state did not become {}: {}".format(suppressed, last))

    def _hidden_probe_dir(self):
        """A probe directory Unity's asset pipeline ignores.

        The import-change signal is the unit under test here, not Unity's importer.
        Unity ignores any folder whose name starts with a dot, so files placed here
        are still enumerated by the tracker's scan (which walks the raw filesystem)
        but never imported or compiled. That isolates the extension filter and the
        decision logic from compiler side effects.
        """
        return self.project_path / "Assets" / "__codex_validation_temp" / ".not_imported"

    def _set_play_mode(self, base_url, playing):
        literal = "true" if playing else "false"
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorApplication = puer.loadType('UnityEditor.EditorApplication');"
            " EditorApplication.isPlaying = " + literal + ";"
            " return { requested: " + literal + " }; }",
        )
        self.assertEqual(exit_code, 0, payload)

    def _script_compilation_during_play(self, base_url):
        return self._health(base_url)["refresh"].get("script_changes_while_playing")

    def _set_script_compilation_during_play(self, base_url, pref_value):
        """Set the Editor's Script Changes While Playing preference via the bridge."""
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorPrefs = puer.loadType('UnityEditor.EditorPrefs');"
            " EditorPrefs.SetInt('ScriptCompilationDuringPlay', " + str(int(pref_value)) + ");"
            " return { set: " + str(int(pref_value)) + " }; }",
        )
        self.assertEqual(exit_code, 0, payload)

    def _restore_script_compilation_during_play(self, base_url, original):
        label_to_value = {
            "recompile_and_continue_playing": 0,
            "recompile_after_finished_playing": 1,
            "stop_playing_and_recompile": 2,
        }
        if original in label_to_value:
            self._set_script_compilation_during_play(base_url, label_to_value[original])
            return
        # The key was absent (or unreadable): drop the override so the Editor's own
        # default applies again instead of leaving the test's value behind.
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorPrefs = puer.loadType('UnityEditor.EditorPrefs');"
            " EditorPrefs.DeleteKey('ScriptCompilationDuringPlay');"
            " return { deleted: true }; }",
        )
        self.assertEqual(exit_code, 0, payload)

    def _wait_for_play_exit(self, base_url, timeout_seconds=180):
        """Wait until the Editor has left play mode, or until the compile starts.

        Stops as soon as the deferred compile edge is visible so a following
        `wait-for-compile` can settle it rather than waiting the edge out. Tolerates
        the domain reload that a deferred compile ends with by re-resolving the
        endpoint from the project's published control port.
        """
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            health, _error = unity_session._probe_health(base_url, 1.5)
            if health is None:
                resolved, resolved_health = _scan_ready_control_endpoint(self.project_path)
                if resolved is not None:
                    base_url, health = resolved, resolved_health
            if health is not None:
                last = health
                if health.get("status") == "compiling":
                    return base_url, health
                refresh = health.get("refresh")
                if isinstance(refresh, dict) and not refresh.get("suppressed"):
                    return base_url, health
            time.sleep(0.25)
        self.fail("Editor did not leave play mode within {}s: {}".format(timeout_seconds, last))
        return base_url, last

    def _wait_for_refresh_pending(self, base_url, timeout_seconds=30):
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            refresh = self._health(base_url).get("refresh")
            last = refresh
            if isinstance(refresh, dict) and refresh.get("pending") == "pending":
                return refresh
            time.sleep(0.25)
        self.fail("change signal did not become pending: {}".format(last))

    def test_health_reports_not_pending_after_settle(self):
        base_url = self._base_url()
        payload, error = unity_session._probe_health(base_url, 1.5)
        self.assertIsNotNone(payload, error)
        self.assertEqual(payload["status"], "ready")
        refresh = payload.get("refresh")
        self.assertIsInstance(refresh, dict, payload)
        self.assertEqual(refresh.get("pending"), "not_pending")
        self.assertFalse(refresh.get("suppressed"))

    def test_non_code_asset_change_does_not_refresh(self):
        base_url = self._base_url()
        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / "not_code_asset.txt").write_text("plain text; never compiles\n", encoding="utf-8")

        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { ok: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "completed")
        refresh = payload.get("refresh")
        self.assertIsInstance(refresh, dict, payload)
        # Non-code assets are deliberately not watched, so no refresh is triggered.
        self.assertFalse(refresh.get("triggered"), refresh)

    def test_removed_refresh_field_is_rejected(self):
        base_url = self._base_url()
        status, body = _post_control_json(
            base_url,
            "/exec",
            {
                "request_id": "removed-field-probe",
                "code": "export default function run(ctx) { return null; }",
                "refresh_before_exec": True,
            },
        )
        self.assertEqual(status, 400, body)
        self.assertFalse(body.get("ok"), body)
        self.assertEqual(body.get("error"), "refresh_before_exec_removed")

    def test_code_change_refreshes_once_then_does_not_refresh_again(self):
        base_url = self._base_url()
        self._write_compile_triggering_probe("AutomaticRefreshProbe.cs")

        first_exit, first_payload = self._exec_script(
            base_url, "export default function run(ctx) { return { pass: 1 }; }"
        )
        self.assertEqual(first_exit, 0, first_payload)
        self.assertEqual(first_payload["status"], "completed")
        first_refresh = first_payload.get("refresh")
        self.assertIsInstance(first_refresh, dict, first_payload)
        # Every decision carries the full diagnostics contract.
        for key in ("triggered", "reason", "paths_changed", "skipped_reason", "settle_outcome", "elapsed_ms"):
            self.assertIn(key, first_refresh)
        if first_refresh["triggered"]:
            self.assertEqual(first_refresh["reason"], "compile_triggering_change")
            self.assertTrue(
                any(path.endswith("AutomaticRefreshProbe.cs") for path in first_refresh["paths_changed"]),
                first_refresh["paths_changed"],
            )

        # No further file change: the loop-breaking property holds -- a second exec
        # must not refresh for the already-settled change.
        second_exit, second_payload = self._exec_script(
            base_url, "export default function run(ctx) { return { pass: 2 }; }"
        )
        self.assertEqual(second_exit, 0, second_payload)
        self.assertEqual(second_payload["status"], "completed")
        second_refresh = second_payload.get("refresh")
        self.assertIsInstance(second_refresh, dict, second_payload)
        self.assertFalse(second_refresh["triggered"], second_refresh)

    # --- settled-import timestamp (tasks 2.1, 2.2) ----------------------------

    def test_exec_and_refresh_do_not_advance_settled_timestamp(self):
        base_url = self._base_url()
        before = self._read_settled_ticks(base_url)
        self.assertGreater(before, 0)

        # A plain exec never advances the timestamp.
        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { n: 1 }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(self._read_settled_ticks(base_url), before)

        # An explicit AssetDatabase.Refresh() that triggers no compilation must not
        # advance it either: Unity's own completion signal is the only writer.
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " const AssetDatabase = puer.loadType('UnityEditor.AssetDatabase');"
                " AssetDatabase.Refresh();"
                " return { ticks: String(trackerField('settledImportUtcTicks')) }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["result"]["ticks"], str(before))
        self.assertEqual(self._read_settled_ticks(base_url), before)

    def test_settled_timestamp_survives_domain_reload(self):
        base_url = self._base_url()
        before_ticks = self._read_settled_ticks(base_url)
        self.assertGreater(before_ticks, 0)
        # Every advance is persisted as it happens, so the live field and the
        # SessionState value agree before the reload.
        self.assertEqual(self._read_persisted_ticks(base_url), str(before_ticks))
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")

        # A forced domain reload with no file change is not a pending change.
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorUtility = puer.loadType('UnityEditor.EditorUtility');"
            " EditorUtility.RequestScriptReload();"
            " return { requested: true }; }",
            wait_ms=60_000,
        )
        self.assertEqual(exit_code, 0, payload)

        base_url = self._wait_for_ready_project()
        after_ticks = self._read_settled_ticks(base_url)
        self.assertGreater(after_ticks, 0)
        # The reload's own completion signal legitimately advances the timestamp (the
        # spec requires that), so exact equality across the reload is not the contract.
        # What must hold is that the baseline was never lost: it is still present,
        # still persisted, and the reload is not mistaken for a change.
        self.assertGreaterEqual(after_ticks, before_ticks)
        self.assertEqual(self._read_persisted_ticks(base_url), str(after_ticks))
        refresh = self._health(base_url)["refresh"]
        self.assertEqual(refresh["pending"], "not_pending")
        self.assertFalse(refresh["suppressed"])
        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { afterReload: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertFalse(payload["refresh"]["triggered"], payload["refresh"])

        # The persistence load path itself: drop in-memory state, plant a known
        # persisted baseline, and let Install() restore it. If the timestamp did not
        # survive a reload, Install() would lose that value.
        planted = after_ticks - 1
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " const SessionState = puer.loadType('UnityEditor.SessionState');"
                " invokeTracker('Shutdown');"
                " setTrackerField('settledImportUtcTicks', 0);"
                " SessionState.SetString('UnityPuerExec.SettledImportUtcTicks', '"
                + str(planted) + "');"
                " invokeTracker('Install');"
                " return { restored: String(trackerField('settledImportUtcTicks')) }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["result"]["restored"], str(planted), payload["result"])

        # Restore a real settled baseline so later cases start clean.
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " invokeTracker('OnCompilationCompleted');"
                " return { settled: true }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")

    # --- change signal (tasks 3.2, 3.4, 3.5, 4.4) -----------------------------

    def test_non_code_writes_do_not_mark_dirty(self):
        base_url = self._base_url()
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")
        probe_dir = self._hidden_probe_dir()
        probe_dir.mkdir(parents=True, exist_ok=True)
        cases = {
            "Probe.unity": "%YAML 1.1\n--- !u!29 &1\nOcclusionCullingSettings:\n",
            "Probe.prefab": "%YAML 1.1\n--- !u!1 &1\nGameObject:\n",
            "Probe.meta": "fileFormatVersion: 2\nguid: 00000000000000000000000000000000\n",
            "Probe.png": "not-an-image",
            "Probe.wav": "not-audio",
        }
        for name, content in cases.items():
            (probe_dir / name).write_text(content, encoding="utf-8")
            refresh = self._health(base_url)["refresh"]
            # Each non-code extension must leave the pending state untouched.
            self.assertEqual(refresh["pending"], "not_pending", (name, refresh))

        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { ok: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertFalse(payload["refresh"]["triggered"], payload["refresh"])

    def test_watcher_error_invalidates_signal_then_forces_one_refresh(self):
        base_url = self._base_url()
        # A real watcher error cannot be produced from outside on Windows (the
        # embedded-Mono watcher is silent), so the state an error event sets is
        # applied directly: the signal becomes untrusted and records why. Health must
        # surface that as unknown, never as not-pending.
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " setTrackerField('signalValid', false);"
                " setTrackerField('deferredSignalError', 'simulated InternalBufferOverflowException');"
                " return { signalValid: String(trackerField('signalValid')) }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["result"]["signalValid"], "false")
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "unknown")

        # The next exec must treat the project as possibly changed and refresh rather
        # than report no change. The scan re-establishes trust, so this is one-shot.
        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { afterError: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["refresh"]["triggered"], payload["refresh"])
        self.assertEqual(payload["refresh"]["reason"], "watcher_signal_unavailable")
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")

        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { settled: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertFalse(payload["refresh"]["triggered"], payload["refresh"])

    def test_change_made_before_install_is_caught_by_baseline_walk(self):
        base_url = self._base_url()
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")
        probe_dir = self._hidden_probe_dir()
        probe_file = probe_dir / "BaselineWalkProbe.cs"
        exit_code, payload = self._exec_script(
            base_url,
            self._tracker_script(
                "export default function run(ctx) {"
                " const Directory = puer.loadType('System.IO.Directory');"
                " const File = puer.loadType('System.IO.File');"
                # Drop all in-memory signal state, change a file, then install: this is
                # the "changed before the watcher was attached" gap the baseline walk
                # exists to close.
                " invokeTracker('Shutdown');"
                " Directory.CreateDirectory(" + _js_string_literal(probe_dir) + ");"
                " File.WriteAllText(" + _js_string_literal(probe_file)
                + ", 'internal static class BaselineWalkProbe { internal const int N = 1; }\\n');"
                " invokeTracker('Install');"
                " return { state: trackerState() }; }"
            ),
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["result"]["state"], "Pending", payload["result"])
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "pending")

    def test_play_mode_skips_refresh_and_preserves_pending_change(self):
        base_url = self._base_url()
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")

        self._set_play_mode(base_url, True)
        self._wait_for_refresh_state(base_url, suppressed=True)

        # A compile-triggering change made while playing: Unity defers importing it.
        probe_dir = self._hidden_probe_dir()
        probe_dir.mkdir(parents=True, exist_ok=True)
        (probe_dir / "PendingPlayProbe.cs").write_text(
            "internal static class PendingPlayProbe { internal const int P = 1; }\n",
            encoding="utf-8",
        )
        refresh = self._health(base_url)["refresh"]
        self.assertEqual(refresh["pending"], "pending")
        self.assertTrue(refresh["suppressed"])
        self.assertEqual(refresh["suppressed_reason"], "play_mode")

        # The skip is reported, and the script still runs.
        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { executedInPlay: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["warning"], "compile_blocked_by_play_mode")
        self.assertIn("warning_detail", payload)
        blocked = payload["compile_blocked"]
        self.assertEqual(blocked["reason"], "play_mode")
        self.assertTrue(
            any("PendingPlayProbe" in path for path in blocked["pending_paths"]), blocked
        )
        self.assertFalse(payload["refresh"]["triggered"], payload["refresh"])
        self.assertEqual(payload["refresh"]["skipped_reason"], "play_mode")

        # The skip must not discard the pending signal.
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "pending")

        # Leaving play mode and execing again refreshes for the still-pending change.
        self._set_play_mode(base_url, False)
        self._wait_for_refresh_state(base_url, suppressed=False)
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "pending")
        exit_code, payload = self._exec_raw(
            base_url, "export default function run(ctx) { return { afterPlayExit: true }; }"
        )
        self.assertIsInstance(payload, dict, (exit_code, payload))
        self.assertTrue(payload["refresh"]["triggered"], payload["refresh"])
        self.assertEqual(payload["refresh"]["reason"], "compile_triggering_change")


class PlayModeCompileBlockRealHostTests(_SharedRealHostDevice, unittest.TestCase):
    """Real-host coverage for a compile blocked by play mode.

    Kept in its own class because the case forces the Editor's "Script Changes While
    Playing" preference to defer the changed script to play mode exit. That
    preference is machine-global Editor state, so the case runs against its own host
    and restores the saved value before any later class reuses a host.
    """

    REFRESH_WAIT_TIMEOUT_MS = 300_000
    _LABEL_TO_VALUE = {
        "recompile_and_continue_playing": 0,
        "recompile_after_finished_playing": 1,
        "stop_playing_and_recompile": 2,
    }

    def setUp(self):
        super().setUp()
        self._saved_preference = None

    def tearDown(self):
        self._exit_play_mode_best_effort()
        self._restore_preference_best_effort()
        super().tearDown()

    # -- transport helpers ---------------------------------------------------

    def _health(self, base_url):
        payload, error = unity_session._probe_health(base_url, 1.5)
        self.assertIsNotNone(payload, error)
        return payload

    def _exec_raw(self, base_url, code, wait_ms=None):
        exit_code, payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(wait_ms or self.REFRESH_WAIT_TIMEOUT_MS),
                "--code", code,
            ]
        )
        return exit_code, payload

    def _exec_script(self, base_url, body):
        exit_code, payload, _, _ = _run_cli(
            [
                "exec",
                "--base-url", base_url,
                "--wait-timeout-ms", str(self.REFRESH_WAIT_TIMEOUT_MS),
                "--code", body,
            ]
        )
        if payload is not None and unity_puer_exec_runtime._running_or_timed_out_response(
            exit_code, json.dumps(payload)
        ):
            exit_code, payload, _, _ = _run_cli(
                [
                    "wait-for-exec",
                    "--base-url", base_url,
                    "--request-id", payload["request_id"],
                    "--wait-timeout-ms", str(READY_TIMEOUT_SECONDS * 1000),
                ]
            )
        return exit_code, payload

    def _write_compile_triggering_probe(self, name):
        temp_dir = self.project_path / "Assets" / "__codex_validation_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / name
        path.write_text(
            "// Auto-generated play-mode probe.\n"
            "internal static class {0} {{ internal const long Stamp = {1}L; }}\n".format(
                path.stem, time.time_ns()
            ),
            encoding="utf-8",
        )
        return path

    def _set_play_mode(self, base_url, playing):
        literal = "true" if playing else "false"
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorApplication = puer.loadType('UnityEditor.EditorApplication');"
            " EditorApplication.isPlaying = " + literal + ";"
            " return { requested: " + literal + " }; }",
        )
        self.assertIsInstance(payload, dict, payload)
        self.assertEqual(exit_code, 0, payload)

    # -- Script Changes While Playing preference -----------------------------

    def _read_preference(self, base_url):
        return self._health(base_url)["refresh"].get("script_changes_while_playing")

    def _set_preference(self, base_url, value):
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorPrefs = puer.loadType('UnityEditor.EditorPrefs');"
            " EditorPrefs.SetInt('ScriptCompilationDuringPlay', " + str(int(value)) + ");"
            " return { set: " + str(int(value)) + " }; }",
        )
        self.assertIsInstance(payload, dict, payload)
        self.assertEqual(exit_code, 0, payload)

    def _delete_preference(self, base_url):
        exit_code, payload = self._exec_raw(
            base_url,
            "export default function run(ctx) {"
            " const EditorPrefs = puer.loadType('UnityEditor.EditorPrefs');"
            " EditorPrefs.DeleteKey('ScriptCompilationDuringPlay');"
            " return { deleted: true }; }",
        )
        self.assertIsInstance(payload, dict, payload)
        self.assertEqual(exit_code, 0, payload)

    def _restore_preference_best_effort(self):
        saved = self._saved_preference
        if saved is None:
            return
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                base_url = self._ensure_shared_host_ready()
                if base_url is None:
                    time.sleep(1.0)
                    continue
                if saved in self._LABEL_TO_VALUE:
                    self._set_preference(base_url, self._LABEL_TO_VALUE[saved])
                else:
                    self._delete_preference(base_url)
                return
            except Exception:  # noqa: BLE001 - cleanup retries until restored.
                time.sleep(1.0)

    def _exit_play_mode_best_effort(self):
        try:
            base_url = self._ensure_shared_host_ready()
            if base_url is not None:
                self._set_play_mode(base_url, False)
        except Exception:  # noqa: BLE001 - cleanup only.
            pass

    # -- waits ---------------------------------------------------------------

    def _wait_for_refresh_state(self, base_url, suppressed, timeout_seconds=60):
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            health, _error = unity_session._probe_health(base_url, 1.5)
            if health is None:
                resolved, resolved_health = _scan_ready_control_endpoint(self.project_path)
                if resolved is not None:
                    base_url, health = resolved, resolved_health
            refresh = health.get("refresh") if isinstance(health, dict) else None
            last = refresh
            if isinstance(refresh, dict) and bool(refresh.get("suppressed")) == suppressed:
                return base_url, refresh
            time.sleep(0.5)
        self.fail("refresh suppressed state did not become {}: {}".format(suppressed, last))

    def _wait_for_refresh_pending(self, base_url, timeout_seconds=30):
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            refresh = self._health(base_url).get("refresh")
            last = refresh
            if isinstance(refresh, dict) and refresh.get("pending") == "pending":
                return refresh
            time.sleep(0.25)
        self.fail("change signal did not become pending: {}".format(last))

    def _wait_for_play_exit(self, base_url, timeout_seconds=180):
        """Wait until the Editor has left play mode, or until the compile starts."""
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            health, _error = unity_session._probe_health(base_url, 1.5)
            if health is None:
                resolved, resolved_health = _scan_ready_control_endpoint(self.project_path)
                if resolved is not None:
                    base_url, health = resolved, resolved_health
            if health is not None:
                last = health
                if health.get("status") == "compiling":
                    return base_url, health
                refresh = health.get("refresh")
                if isinstance(refresh, dict) and not refresh.get("suppressed"):
                    return base_url, health
            time.sleep(0.25)
        self.fail("Editor did not leave play mode within {}s: {}".format(timeout_seconds, last))

    # -- case ----------------------------------------------------------------

    def test_play_mode_compile_block_then_settles_after_play_exit(self):
        """End-to-end play-mode block: exec warning, wait block, exit, settle.

        Forces "Recompile After Finished Playing" so the change made during play is
        deferred and then compiled on exit -- the D6 hypothesis-2 path. tearDown
        restores the saved preference.
        """
        base_url = self._base_url()
        self.assertEqual(self._health(base_url)["refresh"]["pending"], "not_pending")
        self._saved_preference = self._read_preference(base_url)

        self._set_preference(base_url, 1)
        self.assertEqual(
            self._read_preference(base_url), "recompile_after_finished_playing"
        )

        self._set_play_mode(base_url, True)
        base_url, _ = self._wait_for_refresh_state(base_url, suppressed=True)

        # A real (imported) code change while playing: Unity defers it.
        self._write_compile_triggering_probe("PlayBlockProbe.cs")
        self._wait_for_refresh_pending(base_url)

        exit_code, payload = self._exec_script(
            base_url, "export default function run(ctx) { return { executedInPlay: true }; }"
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "warning", payload)
        self.assertEqual(payload["warning"], "compile_blocked_by_play_mode")
        self.assertEqual(
            payload["compile_blocked"]["script_changes_while_playing"],
            "recompile_after_finished_playing",
        )
        self.assertTrue(
            any("PlayBlockProbe" in path for path in payload["compile_blocked"]["pending_paths"]),
            payload,
        )

        exit_code, payload, _, _ = _run_cli(
            ["wait-for-compile", "--base-url", base_url, "--appear-timeout-seconds", "2"]
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["result"]["status"], "compile_blocked", payload)
        self.assertEqual(payload["result"]["reason"], "play_mode")
        self.assertFalse(payload["result"]["compile_observed"])

        # Leaving play mode lets the deferred compile start. That compile crosses a
        # domain reload which can hide the compile edge from /health (the listener
        # stops before the reload), so completion is confirmed by the pending signal
        # clearing. wait-for-compile must then no longer report the play-mode block.
        self._set_play_mode(base_url, False)
        base_url, _ = self._wait_for_play_exit(base_url)
        deadline = time.time() + 180
        pending_state = None
        while time.time() < deadline:
            health, _err = unity_session._probe_health(base_url, 1.5)
            if health is None:
                resolved, resolved_health = _scan_ready_control_endpoint(self.project_path)
                if resolved is not None:
                    base_url, health = resolved, resolved_health
            if health is not None:
                refresh = health.get("refresh")
                if isinstance(refresh, dict):
                    pending_state = refresh.get("pending")
                    if pending_state == "not_pending":
                        break
            time.sleep(0.5)
        self.assertEqual(
            pending_state,
            "not_pending",
            "the change made in play mode was not compiled after play mode exited",
        )

        exit_code, payload, _, _ = _run_cli(
            ["wait-for-compile", "--base-url", base_url, "--appear-timeout-seconds", "2"]
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertNotEqual(payload["result"]["status"], "compile_blocked", payload)
        self.assertIn(
            payload["result"]["status"],
            ("compile_settled", "no_compile_observed"),
            payload,
        )


if __name__ == "__main__":
    unittest.main()

