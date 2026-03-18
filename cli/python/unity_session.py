#!/usr/bin/env python3
import csv
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path

import direct_exec_client


UNITY_PROJECT_PATH_ENV = "UNITY_PROJECT_PATH"
ENV_FILE_NAME = ".env"
DEFAULT_READY_TIMEOUT_SECONDS = 180.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0
DEFAULT_ACTIVITY_TIMEOUT_SECONDS = 20.0
DEFAULT_EDITOR_LOG_MAX_LINES = 40
DEFAULT_STOP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 1.0
RECOVERABLE_HEALTH_STATUSES = ("compiling", "not_available")
SESSION_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "session.json"
_DOTENV_LOADED = False


class UnitySessionError(Exception):
    def __init__(self, message, session=None):
        super().__init__(message)
        self.session = session


class UnityLaunchError(UnitySessionError):
    pass


class UnityNotReadyError(UnitySessionError):
    pass


class UnityStalledError(UnitySessionError):
    pass


class UnitySessionStateError(UnitySessionError):
    def __init__(self, status, message, session=None):
        super().__init__(message, session=session)
        self.status = status


class UnitySession:
    def __init__(
        self,
        owner,
        base_url,
        project_path,
        unity_pid=None,
        unity_exe_path=None,
        launched=False,
        process=None,
        effective_log_path=None,
    ):
        self.owner = owner
        self.base_url = base_url.rstrip("/")
        self.project_path = str(project_path)
        self.unity_pid = unity_pid
        self.unity_exe_path = unity_exe_path
        self.launched = launched
        self.process = process
        self.effective_log_path = str(effective_log_path) if effective_log_path else None
        self.diagnostics = {}

    def to_payload(self):
        payload = {
            "owner": self.owner,
            "launched": self.launched,
            "base_url": self.base_url,
            "project_path": self.project_path,
        }
        if self.unity_pid is not None:
            payload["unity_pid"] = self.unity_pid
        if self.unity_exe_path:
            payload["unity_exe_path"] = self.unity_exe_path
        return payload


def _format_wall_time(timestamp):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(timestamp))


def _default_editor_log_path():
    local_app_data = Path.home() / "AppData" / "Local"
    return local_app_data / "Unity" / "Editor" / "Editor.log"


def _read_recent_editor_log_lines(log_path, max_lines):
    path = Path(log_path)
    if not path.exists():
        return []

    with path.open("rb") as handle:
        handle.seek(0, 2)
        file_size = handle.tell()
        read_size = min(file_size, 32 * 1024)
        handle.seek(max(file_size - read_size, 0))
        chunk = handle.read().decode("utf-8", errors="replace")
    lines = chunk.splitlines()
    return lines[-max_lines:]


def _read_editor_log_size(log_path):
    path = Path(log_path)
    if not path.exists():
        return None
    try:
        return path.stat().st_size
    except OSError:
        return None


def _read_editor_log_chunk(log_path, start_offset):
    path = Path(log_path)
    if not path.exists():
        return start_offset, ""

    try:
        file_size = path.stat().st_size
    except OSError:
        return start_offset, ""

    read_offset = start_offset
    if read_offset is None or read_offset < 0 or read_offset > file_size:
        read_offset = 0

    with path.open("rb") as handle:
        handle.seek(read_offset)
        chunk = handle.read().decode("utf-8", errors="replace")
    return file_size, chunk


def _list_unity_pids():
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Unity.exe", "/NH", "/FO", "CSV"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    rows = []
    reader = csv.reader(io.StringIO(result.stdout))
    for row in reader:
        if not row or row[0] == "INFO: No tasks are running which match the specified criteria.":
            continue
        if len(row) < 2 or row[0] != "Unity.exe":
            continue
        try:
            rows.append(int(row[1]))
        except ValueError:
            continue
    return rows


def _is_pid_running(pid):
    if pid is None:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", "PID eq {}".format(pid), "/NH", "/FO", "CSV"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    output = result.stdout.strip()
    return bool(output) and "No tasks are running" not in output


def _probe_health(base_url, timeout_seconds):
    transport = direct_exec_client.HttpTransport()
    health_url = base_url.rstrip("/") + "/health"
    try:
        payload = transport.post_json(health_url, {}, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - dependency-free diagnostics.
        return None, str(exc)
    return payload, None


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _dotenv_path(repo_root=None):
    repo_root = _repo_root() if repo_root is None else Path(repo_root)
    return repo_root / ENV_FILE_NAME


def _load_dotenv_file(dotenv_path, env=None):
    env = os.environ if env is None else env
    dotenv_path = Path(dotenv_path)
    if not dotenv_path.exists():
        return False

    with dotenv_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in env:
                env[key] = value
    return True


def _ensure_dotenv_loaded(env=None, dotenv_path=None, force=False):
    global _DOTENV_LOADED

    env = os.environ if env is None else env
    if _DOTENV_LOADED and not force and dotenv_path is None and env is os.environ:
        return False

    loaded = _load_dotenv_file(_dotenv_path() if dotenv_path is None else dotenv_path, env=env)
    if env is os.environ and dotenv_path is None:
        _DOTENV_LOADED = True
    return loaded


def resolve_project_path(project_path=None, cwd=None, env=None):
    if project_path:
        return Path(project_path)

    env = os.environ if env is None else env
    _ensure_dotenv_loaded(env=env)
    env_project_path = env.get(UNITY_PROJECT_PATH_ENV)
    if env_project_path:
        return Path(env_project_path)

    return Path.cwd() if cwd is None else Path(cwd)


def _session_artifact_path(project_path):
    return Path(project_path) / SESSION_RELATIVE_PATH


def read_session_artifact(project_path):
    session_path = _session_artifact_path(project_path)
    if not session_path.exists():
        return None
    with session_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_session_artifact(project_path, payload):
    session_path = _session_artifact_path(project_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with session_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def _session_artifact_log_path(session_data):
    if not isinstance(session_data, dict):
        return None
    session_marker = session_data.get("session_marker")
    effective_log_path = session_data.get("effective_log_path")
    unity_pid = session_data.get("unity_pid")
    if not isinstance(session_marker, str) or not session_marker:
        return None
    if not isinstance(effective_log_path, str) or not effective_log_path:
        return None
    if unity_pid is not None and not _is_pid_running(unity_pid):
        return None
    return Path(effective_log_path)


def _resolve_effective_log_path(project_path, unity_log_path=None, session_data=None):
    if session_data is None:
        session_data = read_session_artifact(project_path)
    artifact_log_path = _session_artifact_log_path(session_data)
    if artifact_log_path is not None:
        return artifact_log_path
    if unity_log_path:
        return Path(unity_log_path)
    return _default_editor_log_path()


def _session_marker_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    session_marker = payload.get("session_marker")
    if isinstance(session_marker, str) and session_marker:
        return session_marker
    return None


def _persist_ready_session_artifact(session, effective_log_path, payload=None):
    session_marker = _session_marker_from_payload(payload)
    if session_marker is None and session.diagnostics:
        session_marker = _session_marker_from_payload(session.diagnostics.get("last_health_payload"))
    if not session_marker:
        return
    write_session_artifact(
        session.project_path,
        {
            "base_url": session.base_url,
            "unity_pid": session.unity_pid,
            "session_marker": session_marker,
            "effective_log_path": str(effective_log_path),
        },
    )


def _detach_session_process(session):
    # After readiness succeeds, the CLI only needs the Unity PID. Dropping the
    # Popen handle avoids leaking a live process object into later GC.
    if session is not None:
        if session.process is not None and session.process.returncode is None:
            session.process.returncode = 0
        session.process = None
    return session


def _get_unity_version(project_path):
    project_version_path = Path(project_path) / "ProjectSettings" / "ProjectVersion.txt"
    try:
        with project_version_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("m_EditorVersion:"):
                    return line.split(":", 1)[1].strip()
    except OSError as exc:
        raise UnityLaunchError("failed to read Unity version: {}".format(exc))
    raise UnityLaunchError("failed to read Unity version from {}".format(project_version_path))


def _find_unity_editor_dir(version):
    import os as os_module
    import winreg

    uninstall_reg_paths = (
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    for uninstall_reg_path in uninstall_reg_paths:
        try:
            uninstall_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_reg_path)
        except FileNotFoundError:
            continue
        with uninstall_key:
            for index in range(winreg.QueryInfoKey(uninstall_key)[0]):
                sub_key_name = winreg.EnumKey(uninstall_key, index)
                if not sub_key_name.startswith("Unity "):
                    continue
                with winreg.OpenKey(uninstall_key, sub_key_name) as sub_key:
                    try:
                        display_version = winreg.QueryValueEx(sub_key, "DisplayVersion")[0]
                        if not display_version.startswith(version):
                            continue
                        uninstall_string = winreg.QueryValueEx(sub_key, "UninstallString")[0]
                    except FileNotFoundError:
                        continue
                    return os_module.path.dirname(uninstall_string)
    raise UnityLaunchError("Unity {} not found".format(version))


def _resolve_unity_exe_path(project_path, unity_exe_path):
    if unity_exe_path:
        return str(Path(unity_exe_path))
    try:
        unity_version = _get_unity_version(project_path)
        unity_editor_dir = _find_unity_editor_dir(unity_version)
        return str(Path(unity_editor_dir) / "Unity.exe")
    except Exception as exc:  # noqa: BLE001 - normalize launcher error.
        if isinstance(exc, UnityLaunchError):
            raise
        raise UnityLaunchError("failed to resolve Unity.exe: {}".format(exc))


def _launch_unity(project_path, unity_exe_path, unity_log_path=None):
    args = [
        unity_exe_path,
        "-projectPath",
        str(project_path),
    ]
    if unity_log_path:
        args.extend(["-logFile", str(unity_log_path)])
    try:
        process = subprocess.Popen(args)
    except OSError as exc:
        raise UnityLaunchError("failed to launch Unity: {}".format(exc))
    return process


def _collect_diagnostics(base_url, log_path, health_error, activity_state=None, health_payload=None):
    diagnostics = {
        "unity_pids": _list_unity_pids(),
        "editor_log_path": str(log_path),
        "editor_log_exists": Path(log_path).exists(),
        "recent_editor_log_lines": _read_recent_editor_log_lines(log_path, DEFAULT_EDITOR_LOG_MAX_LINES),
    }
    if health_error is not None:
        diagnostics["last_health_error"] = health_error
    if health_payload is not None:
        diagnostics["last_health_payload"] = health_payload
    elif health_error is None:
        payload, _ = _probe_health(base_url, DEFAULT_HEALTH_TIMEOUT_SECONDS)
        if payload is not None:
            diagnostics["last_health_payload"] = payload
    if activity_state is not None:
        diagnostics["last_log_size"] = activity_state.get("last_log_size")
        diagnostics["last_activity_time"] = activity_state.get("last_activity_time")
        diagnostics["idle_seconds"] = activity_state.get("idle_seconds")
    return diagnostics


def _create_activity_tracker(log_path):
    now = time.time()
    return {
        "last_log_size": _read_editor_log_size(log_path),
        "last_activity_monotonic": now,
        "last_activity_time": _format_wall_time(now),
        "idle_seconds": 0.0,
    }


def _update_activity_tracker(activity_tracker, log_path):
    current_log_size = _read_editor_log_size(log_path)
    if current_log_size is not None and current_log_size != activity_tracker["last_log_size"]:
        now = time.time()
        activity_tracker["last_log_size"] = current_log_size
        activity_tracker["last_activity_monotonic"] = now
        activity_tracker["last_activity_time"] = _format_wall_time(now)

    activity_tracker["idle_seconds"] = round(
        max(0.0, time.time() - activity_tracker["last_activity_monotonic"]),
        3,
    )
    return activity_tracker


def _build_activity_state(activity_tracker):
    return {
        "last_log_size": activity_tracker["last_log_size"],
        "last_activity_time": activity_tracker["last_activity_time"],
        "idle_seconds": activity_tracker["idle_seconds"],
    }


def _finalize_session_diagnostics(session, log_path, health_error, activity_tracker, last_payload=None):
    session.diagnostics = _collect_diagnostics(
        session.base_url,
        log_path,
        health_error,
        _build_activity_state(activity_tracker),
        health_payload=last_payload,
    )


def _build_health_snapshot(payload, error):
    if payload is not None:
        snapshot = {
            "ok": payload.get("ok"),
            "status": payload.get("status"),
        }
        if "port" in payload:
            snapshot["port"] = payload.get("port")
        return snapshot
    return {"ok": False, "status": "transport_error", "error": error}


def _wait_for_session(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    completion_predicate=None,
    timeout_message=None,
    iteration_observer=None,
):
    log_path = Path(log_path or session.effective_log_path or _default_editor_log_path())
    deadline = time.time() + timeout_seconds
    last_health_error = None
    last_payload = None
    activity_tracker = _create_activity_tracker(log_path)
    completion_predicate = completion_predicate or (lambda payload: payload.get("ok") and payload.get("status") == "ready")

    while time.time() < deadline:
        payload, error = _probe_health(session.base_url, health_timeout_seconds)
        if iteration_observer is not None:
            iteration_observer(payload, error)
        if payload is not None:
            last_payload = payload
            if completion_predicate(payload):
                _update_activity_tracker(activity_tracker, log_path)
                _finalize_session_diagnostics(session, log_path, None, activity_tracker, last_payload=payload)
                return session
            last_health_error = json.dumps(payload, ensure_ascii=True)
        else:
            last_health_error = error

        _update_activity_tracker(activity_tracker, log_path)

        if session.launched and session.process is not None and session.process.poll() is not None:
            _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["unity_exit_code"] = session.process.returncode
            raise UnityLaunchError(
                "Unity exited before ready with code {}".format(session.process.returncode),
                session=session,
            )

        if activity_timeout_seconds is not None and activity_tracker["idle_seconds"] >= activity_timeout_seconds:
            _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            raise UnityStalledError(
                "Unity log activity stalled for {:.1f} seconds".format(activity_tracker["idle_seconds"]),
                session=session,
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    _update_activity_tracker(activity_tracker, log_path)
    _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
    raise UnityNotReadyError(
        timeout_message or "Unity did not become ready within {} seconds".format(timeout_seconds),
        session=session,
    )


def wait_until_healthy(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
):
    return _wait_for_session(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        completion_predicate=lambda payload: payload.get("ok") and payload.get("status") == "ready",
        timeout_message="Unity did not become healthy within {} seconds".format(timeout_seconds),
    )


def wait_until_recovered(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    recoverable_statuses=RECOVERABLE_HEALTH_STATUSES,
):
    observed_health = []
    recovery_seen = {"value": False}

    def observe(payload, error):
        snapshot = _build_health_snapshot(payload, error)
        if not observed_health or observed_health[-1] != snapshot:
            observed_health.append(snapshot)
        status = snapshot.get("status")
        if status in recoverable_statuses or status == "transport_error":
            recovery_seen["value"] = True

    result = _wait_for_session(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        completion_predicate=lambda payload: payload.get("ok") and payload.get("status") == "ready",
        timeout_message="Unity did not recover to healthy within {} seconds".format(timeout_seconds),
        iteration_observer=observe,
    )
    result.diagnostics["wait_kind"] = "recovery"
    result.diagnostics["observed_health"] = observed_health
    result.diagnostics["recovery_observed"] = recovery_seen["value"]
    result.diagnostics["recovery_not_needed"] = not recovery_seen["value"]
    return result


def wait_for_log_pattern(
    session,
    pattern,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    start_offset=None,
    extract_group=None,
    extract_json_group=None,
    expected_session_marker=None,
):
    compiled_pattern = re.compile(pattern)
    log_path = Path(log_path or session.effective_log_path or _default_editor_log_path())
    deadline = time.time() + timeout_seconds
    last_health_error = None
    last_payload = None
    activity_tracker = _create_activity_tracker(log_path)
    scan_offset = start_offset if start_offset is not None else _read_editor_log_size(log_path)

    while time.time() < deadline:
        payload, error = _probe_health(session.base_url, health_timeout_seconds)
        if payload is not None:
            last_payload = payload
            last_health_error = json.dumps(payload, ensure_ascii=True)
            if expected_session_marker is not None:
                observed_session_marker = payload.get("session_marker")
                if not isinstance(observed_session_marker, str) or not observed_session_marker:
                    _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
                    raise UnitySessionStateError(
                        "session_missing",
                        "observation target did not provide session continuity information",
                        session=session,
                    )
                if observed_session_marker != expected_session_marker:
                    _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
                    raise UnitySessionStateError(
                        "session_stale",
                        "observation target session has changed since the expected session marker was recorded",
                        session=session,
                    )
        else:
            last_health_error = error

        chunk_start_offset = scan_offset
        scan_offset, chunk = _read_editor_log_chunk(log_path, scan_offset)
        _update_activity_tracker(activity_tracker, log_path)
        match = compiled_pattern.search(chunk)
        if match is not None:
            _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["matched_log_pattern"] = pattern
            session.diagnostics["matched_log_text"] = match.group(0)
            session.diagnostics["matched_log_offset"] = chunk_start_offset + len(chunk[: match.end()].encode("utf-8"))
            if extract_group is not None:
                session.diagnostics["extracted_group"] = match.group(extract_group)
            if extract_json_group is not None:
                session.diagnostics["extracted_json"] = json.loads(match.group(extract_json_group))
            return session

        if session.launched and session.process is not None and session.process.poll() is not None:
            _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["unity_exit_code"] = session.process.returncode
            raise UnityLaunchError(
                "Unity exited before log pattern matched with code {}".format(session.process.returncode),
                session=session,
            )

        if activity_timeout_seconds is not None and activity_tracker["idle_seconds"] >= activity_timeout_seconds:
            _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            raise UnityStalledError(
                "Unity log activity stalled for {:.1f} seconds while waiting for log pattern".format(
                    activity_tracker["idle_seconds"]
                ),
                session=session,
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    _update_activity_tracker(activity_tracker, log_path)
    _finalize_session_diagnostics(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
    session.diagnostics["expected_log_pattern"] = pattern
    raise UnityNotReadyError(
        "Unity did not emit log pattern within {} seconds".format(timeout_seconds),
        session=session,
    )


def wait_ready_with_activity(
    session,
    ready_timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
):
    return wait_until_healthy(
        session,
        ready_timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
    )


def ensure_session_ready(
    project_path=None,
    base_url=direct_exec_client.DEFAULT_BASE_URL,
    unity_exe_path=None,
    ready_timeout_seconds=DEFAULT_READY_TIMEOUT_SECONDS,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    unity_log_path=None,
):
    project_path = resolve_project_path(project_path)
    session_data = read_session_artifact(project_path)
    log_path = _resolve_effective_log_path(project_path, unity_log_path=unity_log_path, session_data=session_data)

    initial_pids = _list_unity_pids()
    payload, error = _probe_health(base_url, health_timeout_seconds)
    if payload is not None and payload.get("ok") and payload.get("status") == "ready":
        session = UnitySession(
            owner="existing_service",
            base_url=base_url,
            project_path=project_path,
            unity_pid=initial_pids[0] if initial_pids else None,
            launched=False,
            effective_log_path=log_path,
        )
        activity_state = {
            "last_log_size": _read_editor_log_size(log_path),
            "last_activity_time": _format_wall_time(time.time()),
            "idle_seconds": 0.0,
        }
        session.diagnostics = _collect_diagnostics(base_url, log_path, None, activity_state)
        session.diagnostics["last_health_payload"] = payload
        _persist_ready_session_artifact(session, log_path, payload=payload)
        return session

    if initial_pids:
        session = UnitySession(
            owner="existing_process",
            base_url=base_url,
            project_path=project_path,
            unity_pid=initial_pids[0],
            launched=False,
            effective_log_path=log_path,
        )
        session.diagnostics = _collect_diagnostics(base_url, log_path, error)
        session = wait_ready_with_activity(
            session,
            ready_timeout_seconds,
            activity_timeout_seconds=activity_timeout_seconds,
            health_timeout_seconds=health_timeout_seconds,
            log_path=log_path,
        )
        _persist_ready_session_artifact(session, log_path)
        return _detach_session_process(session)

    resolved_unity_exe_path = _resolve_unity_exe_path(project_path, unity_exe_path)
    process = _launch_unity(project_path, resolved_unity_exe_path, unity_log_path=unity_log_path)
    session = UnitySession(
        owner="launched",
        base_url=base_url,
        project_path=project_path,
        unity_pid=process.pid,
        unity_exe_path=resolved_unity_exe_path,
        launched=True,
        process=process,
        effective_log_path=log_path,
    )
    session.diagnostics = _collect_diagnostics(base_url, log_path, error)
    session = wait_ready_with_activity(
        session,
        ready_timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
    )
    _persist_ready_session_artifact(session, log_path)
    return _detach_session_process(session)


def get_log_source(project_path=None, base_url=None, unity_log_path=None):
    resolved_project_path = resolve_project_path(project_path)
    if base_url is not None:
        log_path = _default_editor_log_path()
        if not log_path.exists():
            return None
    else:
        session_data = read_session_artifact(resolved_project_path)
        log_path = _resolve_effective_log_path(resolved_project_path, unity_log_path=unity_log_path, session_data=session_data)
        if not log_path.exists() and unity_log_path is None and _session_artifact_log_path(session_data) is None:
            return None

    session = UnitySession(
        owner="observation",
        base_url=(base_url or direct_exec_client.DEFAULT_BASE_URL),
        project_path=resolved_project_path,
        unity_pid=None,
        launched=False,
        effective_log_path=log_path,
    )
    return session, {"status": "log_source_available", "source": "file", "path": str(log_path)}


def create_direct_session(base_url, project_path=None):
    return UnitySession(
        owner="direct_service",
        base_url=base_url,
        project_path=resolve_project_path(project_path),
        launched=False,
    )


def create_observation_session(project_path=None, base_url=None, unity_log_path=None):
    resolved_project_path = resolve_project_path(project_path)
    session_data = read_session_artifact(resolved_project_path)
    unity_pid = None
    effective_base_url = base_url or direct_exec_client.DEFAULT_BASE_URL
    owner = "observation"
    log_path = _resolve_effective_log_path(resolved_project_path, unity_log_path=unity_log_path, session_data=session_data)
    if session_data is not None:
        effective_base_url = session_data.get("base_url") or effective_base_url
        unity_pid = session_data.get("unity_pid")
        if _session_artifact_log_path(session_data) is not None:
            owner = "session_artifact"
    elif not _list_unity_pids() and unity_log_path is None and not log_path.exists():
        return None

    session = UnitySession(
        owner=owner,
        base_url=effective_base_url,
        project_path=resolved_project_path,
        unity_pid=unity_pid,
        launched=False,
        effective_log_path=log_path,
    )
    session.diagnostics = _collect_diagnostics(session.base_url, log_path, None)
    return session


def inspect_direct_service(base_url, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS):
    payload, error = _probe_health(base_url, health_timeout_seconds)
    if payload is not None:
        return payload.get("ok") and payload.get("status") == "ready", payload, error
    return False, None, error


def ensure_stopped(project_path=None, base_url=None, mode="inspect", timeout_seconds=DEFAULT_STOP_TIMEOUT_SECONDS):
    if base_url:
        is_ready, payload, error = inspect_direct_service(base_url)
        session = create_direct_session(base_url)
        if payload is not None:
            session.diagnostics["last_health_payload"] = payload
        if error is not None:
            session.diagnostics["last_health_error"] = error
        return (not is_ready), session

    resolved_project_path = resolve_project_path(project_path)
    session_data = read_session_artifact(resolved_project_path)
    session = UnitySession(
        owner="project_control",
        base_url=(session_data or {}).get("base_url", direct_exec_client.DEFAULT_BASE_URL),
        project_path=resolved_project_path,
        unity_pid=(session_data or {}).get("unity_pid"),
        launched=False,
    )
    session.diagnostics = {
        "unity_pids": _list_unity_pids(),
        "session_artifact_path": str(_session_artifact_path(resolved_project_path)),
        "session_artifact_exists": session_data is not None,
    }

    target_pid = session.unity_pid
    if target_pid is None:
        return len(session.diagnostics["unity_pids"]) == 0, session

    if not _is_pid_running(target_pid):
        return True, session

    if mode == "inspect":
        return False, session

    if mode == "timeout_then_kill":
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not _is_pid_running(target_pid):
                return True, session
            time.sleep(POLL_INTERVAL_SECONDS)
        mode = "immediate_kill"

    if mode == "immediate_kill":
        result = subprocess.run(
            ["taskkill", "/PID", str(target_pid), "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        session.diagnostics["taskkill_stdout"] = result.stdout.strip()
        session.diagnostics["taskkill_stderr"] = result.stderr.strip()
        session.diagnostics["taskkill_exit_code"] = result.returncode
        return not _is_pid_running(target_pid), session

    return False, session


def close_session(session, keep_unity=False):
    cleanup = {
        "attempted": False,
        "kept": keep_unity or not session.launched,
        "closed": False,
    }
    if not session.launched or keep_unity:
        return cleanup

    cleanup["attempted"] = True

    if not _is_pid_running(session.unity_pid):
        cleanup["closed"] = True
        cleanup["already_stopped"] = True
        return cleanup

    result = subprocess.run(
        ["taskkill", "/PID", str(session.unity_pid), "/T", "/F"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    cleanup["stdout"] = result.stdout.strip()
    cleanup["stderr"] = result.stderr.strip()
    cleanup["closed"] = result.returncode == 0 or not _is_pid_running(session.unity_pid)
    if result.returncode != 0 and not cleanup["closed"]:
        cleanup["error"] = "taskkill failed with code {}".format(result.returncode)
    return cleanup
