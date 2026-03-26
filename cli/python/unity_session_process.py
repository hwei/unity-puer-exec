#!/usr/bin/env python3
import csv
import io
import subprocess
import time as time_module
from pathlib import Path

from unity_session_common import DEFAULT_STOP_TIMEOUT_SECONDS, POLL_INTERVAL_SECONDS, UnityLaunchError, UnitySession


def list_unity_pids():
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


def is_pid_running(pid):
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


def detach_session_process(session):
    # After readiness succeeds, the CLI only needs the Unity PID. Dropping the
    # Popen handle avoids leaking a live process object into later GC.
    if session is not None:
        if session.process is not None and session.process.returncode is None:
            session.process.returncode = 0
        session.process = None
    return session


def get_unity_version(project_path):
    project_version_path = Path(project_path) / "ProjectSettings" / "ProjectVersion.txt"
    try:
        with project_version_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("m_EditorVersion:"):
                    return line.split(":", 1)[1].strip()
    except OSError as exc:
        raise UnityLaunchError("failed to read Unity version: {}".format(exc))
    raise UnityLaunchError("failed to read Unity version from {}".format(project_version_path))


def find_unity_editor_dir(version):
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


def resolve_unity_exe_path(project_path, unity_exe_path, get_unity_version_fn=None, find_unity_editor_dir_fn=None):
    if unity_exe_path:
        return str(Path(unity_exe_path))
    get_unity_version_fn = get_unity_version if get_unity_version_fn is None else get_unity_version_fn
    find_unity_editor_dir_fn = find_unity_editor_dir if find_unity_editor_dir_fn is None else find_unity_editor_dir_fn
    try:
        unity_version = get_unity_version_fn(project_path)
        unity_editor_dir = find_unity_editor_dir_fn(unity_version)
        return str(Path(unity_editor_dir) / "Unity.exe")
    except Exception as exc:  # noqa: BLE001 - normalize launcher error.
        if isinstance(exc, UnityLaunchError):
            raise
        raise UnityLaunchError("failed to resolve Unity.exe: {}".format(exc))


def launch_unity(project_path, unity_exe_path, unity_log_path=None):
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


def ensure_stopped(
    project_path=None,
    mode="inspect",
    timeout_seconds=DEFAULT_STOP_TIMEOUT_SECONDS,
    resolve_project_path_fn=None,
    read_session_artifact_fn=None,
    session_artifact_path_fn=None,
    list_unity_pids_fn=None,
    is_pid_running_fn=None,
    default_base_url=None,
    time_ref=None,
):
    list_unity_pids_fn = list_unity_pids if list_unity_pids_fn is None else list_unity_pids_fn
    is_pid_running_fn = is_pid_running if is_pid_running_fn is None else is_pid_running_fn
    time_ref = time_module if time_ref is None else time_ref

    resolved_project_path = resolve_project_path_fn(project_path)
    session_data = read_session_artifact_fn(resolved_project_path)
    session = UnitySession(
        owner="project_control",
        base_url=(session_data or {}).get("base_url", default_base_url),
        project_path=resolved_project_path,
        unity_pid=(session_data or {}).get("unity_pid"),
        launched=False,
    )
    session.diagnostics = {
        "unity_pids": list_unity_pids_fn(),
        "session_artifact_path": str(session_artifact_path_fn(resolved_project_path)),
        "session_artifact_exists": session_data is not None,
    }

    target_pid = session.unity_pid
    if target_pid is None:
        return len(session.diagnostics["unity_pids"]) == 0, session

    if not is_pid_running_fn(target_pid):
        return True, session

    if mode == "inspect":
        return False, session

    if mode == "timeout_then_kill":
        deadline = time_ref.time() + timeout_seconds
        while time_ref.time() < deadline:
            if not is_pid_running_fn(target_pid):
                return True, session
            time_ref.sleep(POLL_INTERVAL_SECONDS)
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
        settle_deadline = time_ref.time() + max(POLL_INTERVAL_SECONDS, min(timeout_seconds, 2.0))
        while time_ref.time() < settle_deadline:
            if not is_pid_running_fn(target_pid):
                return True, session
            time_ref.sleep(POLL_INTERVAL_SECONDS)
        return not is_pid_running_fn(target_pid), session

    return False, session


def close_session(session, keep_unity=False, is_pid_running_fn=None):
    is_pid_running_fn = is_pid_running if is_pid_running_fn is None else is_pid_running_fn
    cleanup = {
        "attempted": False,
        "kept": keep_unity or not session.launched,
        "closed": False,
    }
    if not session.launched or keep_unity:
        return cleanup

    cleanup["attempted"] = True

    if not is_pid_running_fn(session.unity_pid):
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
    cleanup["closed"] = result.returncode == 0 or not is_pid_running_fn(session.unity_pid)
    if result.returncode != 0 and not cleanup["closed"]:
        cleanup["error"] = "taskkill failed with code {}".format(result.returncode)
    return cleanup
