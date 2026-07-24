#!/usr/bin/env python3
import csv
import io
import os
import subprocess
import time as time_module
from pathlib import Path

from unity_session_common import (
    CLI_OWNED_UNITY_LAUNCH_SWITCHES,
    CONTROL_ACTIVATION_SWITCH,
    DEFAULT_STOP_TIMEOUT_SECONDS,
    POLL_INTERVAL_SECONDS,
    UNITY_LAUNCH_ARGS_ENV,
    UNITY_LOCKFILE_RELATIVE_PATH,
    UnityLaunchError,
    UnitySession,
)


def _is_cli_owned_unity_switch(token):
    if token is None:
        return False
    text = str(token).strip()
    if not text:
        return False
    # Unity switches are matched case-insensitively; a token may be just the
    # switch or "switch=value". Compare the leading switch form only.
    head = text.split("=", 1)[0].lower()
    return head in CLI_OWNED_UNITY_LAUNCH_SWITCHES


def parse_ambient_unity_launch_args(env=None):
    """Read UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS as a JSON array of strings.

    Returns [] when unset or empty. Raises UnityLaunchError on malformed values
    so a launch-driven command fails with a machine-usable reason rather than
    partially applying a guessed token list.
    """
    env = os.environ if env is None else env
    raw = env.get(UNITY_LAUNCH_ARGS_ENV)
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    try:
        import json

        parsed = json.loads(text)
    except Exception as exc:  # noqa: BLE001 - normalize for the launch boundary.
        raise UnityLaunchError(
            "{} must be a JSON array of strings: {}".format(UNITY_LAUNCH_ARGS_ENV, exc)
        )
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise UnityLaunchError(
            "{} must be a JSON array of strings".format(UNITY_LAUNCH_ARGS_ENV)
        )
    return [item for item in parsed if item != ""]


def merge_unity_launch_args(cli_args=None, env=None):
    """Merge ambient then CLI-flag tokens, dedupe exact matches, reject CLI-owned switches."""
    ambient = parse_ambient_unity_launch_args(env=env)
    flag_tokens = [] if cli_args is None else [str(token) for token in cli_args if token is not None and str(token) != ""]
    merged = []
    seen = set()
    for token in ambient + flag_tokens:
        if token in seen:
            continue
        seen.add(token)
        merged.append(token)
    reserved = [token for token in merged if _is_cli_owned_unity_switch(token)]
    if reserved:
        raise UnityLaunchError(
            "unity launch args cannot rebind CLI-owned switches {}; got {}".format(
                ", ".join(sorted({str(t).split('=', 1)[0] for t in reserved})),
                reserved,
            )
        )
    return merged


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


def _pid_present_in_tasklist_csv(output, pid):
    # Decide liveness from the parsed CSV rather than from the absence of an
    # English "No tasks are running" string: tasklist localizes that
    # informational line, so a sentinel check reports every PID as alive on
    # non-English Windows. A real match is a CSV data row whose PID column
    # (index 1) equals the queried PID; the localized no-match line is not a
    # valid CSV row with an integer PID column and is skipped. Mirrors the
    # locale-robust parsing already used by list_unity_pids.
    reader = csv.reader(io.StringIO(output))
    for row in reader:
        if len(row) < 2:
            continue
        try:
            row_pid = int(row[1])
        except ValueError:
            continue
        if row_pid == pid:
            return True
    return False


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
    return _pid_present_in_tasklist_csv(result.stdout, pid)


def _project_lockfile_is_held(project_path):
    import msvcrt

    lockfile_path = Path(project_path) / UNITY_LOCKFILE_RELATIVE_PATH
    try:
        fd = os.open(str(lockfile_path), os.O_RDWR)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    try:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return False
    finally:
        os.close(fd)


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


def launch_unity(project_path, unity_exe_path, unity_log_path=None, extra_args=None, env=None):
    """Cold-start Unity for a project this CLI owns.

    extra_args are caller-supplied argv tokens (from --unity-launch-arg and/or
    UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS). They are appended after CLI-owned args and
    cannot rebind -projectPath, -logFile, or the activation switch.
    """
    args = [
        unity_exe_path,
        "-projectPath",
        str(project_path),
        # The control service no longer starts implicitly, so a CLI-driven launch
        # has to ask for it. Passing it on every launch is what keeps this change
        # invisible to CLI callers: they still get an Editor that is controllable
        # and, via -logFile below, privately observable.
        CONTROL_ACTIVATION_SWITCH,
    ]
    if unity_log_path:
        args.extend(["-logFile", str(unity_log_path)])
    args.extend(merge_unity_launch_args(cli_args=extra_args, env=env))
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
    read_endpoint_publication_fn=None,
    endpoint_publication_path_fn=None,
    lockfile_held_fn=None,
    is_pid_running_fn=None,
    default_base_url=None,
    time_ref=None,
):
    """Decide whether a project is stopped, from that project's own state.

    Every caller asks "is any Editor still serving this project". The rule this
    replaces answered two different questions instead, and both diverged from that
    one exactly when it mattered. With a session record present it asked "is the pid
    I wrote down earlier gone", which reports stopped while an Editor the record
    never knew about is live and answering -- that is what let a real-host case
    attach to a Hub-launched Editor and observe the shared per-user log. With no
    record it asked "is the machine free of Unity.exe", so any unrelated Editor made
    it report "not stopped" forever, on a machine the project explicitly supports.

    The project's Unity lockfile answers the actual question, for any Editor,
    regardless of who started it and of what else runs on the machine. The
    publication supplies a process to stop when one is needed -- and only ever a
    process the target project's own Editor named, so a stop can no longer reach an
    Editor belonging to a different project.
    """
    is_pid_running_fn = is_pid_running if is_pid_running_fn is None else is_pid_running_fn
    lockfile_held_fn = _project_lockfile_is_held if lockfile_held_fn is None else lockfile_held_fn
    time_ref = time_module if time_ref is None else time_ref

    resolved_project_path = resolve_project_path_fn(project_path)
    publication = read_endpoint_publication_fn(resolved_project_path)
    session = UnitySession(
        owner="project_control",
        base_url=(publication or {}).get("base_url", default_base_url),
        project_path=resolved_project_path,
        unity_pid=(publication or {}).get("unity_pid"),
        launched=False,
    )
    session.diagnostics = {
        "stop_rule": "project_lockfile",
        "endpoint_publication_path": str(endpoint_publication_path_fn(resolved_project_path)),
        "endpoint_publication_exists": publication is not None,
        "project_lockfile_held": lockfile_held_fn(resolved_project_path),
    }

    if not session.diagnostics["project_lockfile_held"]:
        return True, session

    if mode == "inspect":
        return False, session

    if mode == "timeout_then_kill":
        deadline = time_ref.time() + timeout_seconds
        while time_ref.time() < deadline:
            if not lockfile_held_fn(resolved_project_path):
                session.diagnostics["project_lockfile_held"] = False
                return True, session
            time_ref.sleep(POLL_INTERVAL_SECONDS)
        mode = "immediate_kill"

    if mode == "immediate_kill":
        target_pid = session.unity_pid
        if target_pid is None:
            # A held lockfile with nothing published is a running Editor this CLI
            # was never given a handle on. Killing something to make the answer
            # true is exactly the failure this rule exists to prevent, so it
            # reports the Editor instead.
            session.diagnostics["kill_skipped_reason"] = "no_published_process_to_target"
            return False, session

        result = subprocess.run(
            ["taskkill", "/PID", str(target_pid), "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        session.diagnostics["taskkill_target_pid"] = target_pid
        session.diagnostics["taskkill_stdout"] = result.stdout.strip()
        session.diagnostics["taskkill_stderr"] = result.stderr.strip()
        session.diagnostics["taskkill_exit_code"] = result.returncode
        settle_deadline = time_ref.time() + max(POLL_INTERVAL_SECONDS, min(timeout_seconds, 2.0))
        while time_ref.time() < settle_deadline:
            if not lockfile_held_fn(resolved_project_path):
                session.diagnostics["project_lockfile_held"] = False
                return True, session
            time_ref.sleep(POLL_INTERVAL_SECONDS)
        still_held = lockfile_held_fn(resolved_project_path)
        session.diagnostics["project_lockfile_held"] = still_held
        return not still_held, session

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
