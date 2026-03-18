#!/usr/bin/env python3
import time

import direct_exec_client
import unity_session_env
import unity_session_logs
import unity_session_process
import unity_session_wait
from unity_session_common import (
    DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    DEFAULT_EDITOR_LOG_MAX_LINES,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    DEFAULT_READY_TIMEOUT_SECONDS,
    DEFAULT_STOP_TIMEOUT_SECONDS,
    ENV_FILE_NAME,
    POLL_INTERVAL_SECONDS,
    RECOVERABLE_HEALTH_STATUSES,
    SESSION_RELATIVE_PATH,
    UNITY_PROJECT_PATH_ENV,
    UnityLaunchError,
    UnityNotReadyError,
    UnitySession,
    UnitySessionError,
    UnitySessionStateError,
    UnityStalledError,
)


def _format_wall_time(timestamp):
    return unity_session_wait.format_wall_time(timestamp, time_ref=time)


def _repo_root():
    return unity_session_env.repo_root(__file__)


def _dotenv_path(repo_root=None):
    return unity_session_env.dotenv_path(__file__, repo_root_path=repo_root)


def _load_dotenv_file(dotenv_path, env=None):
    return unity_session_env.load_dotenv_file(dotenv_path, env=env)


def _ensure_dotenv_loaded(env=None, dotenv_path=None, force=False):
    return unity_session_env.ensure_dotenv_loaded(__file__, env=env, dotenv_file=dotenv_path, force=force)


def resolve_project_path(project_path=None, cwd=None, env=None):
    return unity_session_env.resolve_project_path(
        __file__,
        project_path=project_path,
        cwd=cwd,
        env=env,
        ensure_dotenv_loaded_fn=_ensure_dotenv_loaded,
    )


def _default_editor_log_path():
    return unity_session_logs.default_editor_log_path()


def _read_recent_editor_log_lines(log_path, max_lines):
    return unity_session_logs.read_recent_editor_log_lines(log_path, max_lines)


def _read_editor_log_size(log_path):
    return unity_session_logs.read_editor_log_size(log_path)


def _read_editor_log_chunk(log_path, start_offset):
    return unity_session_logs.read_editor_log_chunk(log_path, start_offset)


def _list_unity_pids():
    return unity_session_process.list_unity_pids()


def _is_pid_running(pid):
    return unity_session_process.is_pid_running(pid)


def _probe_health(base_url, timeout_seconds):
    return unity_session_wait.probe_health(base_url, timeout_seconds)


def _session_artifact_path(project_path):
    return unity_session_logs.session_artifact_path(project_path)


def read_session_artifact(project_path):
    return unity_session_logs.read_session_artifact(project_path)


def write_session_artifact(project_path, payload):
    return unity_session_logs.write_session_artifact(project_path, payload)


def _session_artifact_log_path(session_data):
    return unity_session_logs.session_artifact_log_path(session_data, is_pid_running_fn=_is_pid_running)


def _resolve_effective_log_path(project_path, unity_log_path=None, session_data=None):
    return unity_session_logs.resolve_effective_log_path(
        project_path,
        unity_log_path=unity_log_path,
        session_data=session_data,
        read_session_artifact_fn=read_session_artifact,
        session_artifact_log_path_fn=_session_artifact_log_path,
        default_editor_log_path_fn=_default_editor_log_path,
    )


def _session_marker_from_payload(payload):
    return unity_session_logs.session_marker_from_payload(payload)


def _persist_ready_session_artifact(session, effective_log_path, payload=None):
    return unity_session_logs.persist_ready_session_artifact(
        session,
        effective_log_path,
        payload=payload,
        session_marker_from_payload_fn=_session_marker_from_payload,
        write_session_artifact_fn=write_session_artifact,
    )


def _detach_session_process(session):
    return unity_session_process.detach_session_process(session)


def _get_unity_version(project_path):
    return unity_session_process.get_unity_version(project_path)


def _find_unity_editor_dir(version):
    return unity_session_process.find_unity_editor_dir(version)


def _resolve_unity_exe_path(project_path, unity_exe_path):
    return unity_session_process.resolve_unity_exe_path(
        project_path,
        unity_exe_path,
        get_unity_version_fn=_get_unity_version,
        find_unity_editor_dir_fn=_find_unity_editor_dir,
    )


def _launch_unity(project_path, unity_exe_path, unity_log_path=None):
    return unity_session_process.launch_unity(project_path, unity_exe_path, unity_log_path=unity_log_path)


def _collect_diagnostics(base_url, log_path, health_error, activity_state=None, health_payload=None):
    return unity_session_wait.collect_diagnostics(
        base_url,
        log_path,
        health_error,
        activity_state=activity_state,
        health_payload=health_payload,
        list_unity_pids_fn=_list_unity_pids,
        read_recent_editor_log_lines_fn=_read_recent_editor_log_lines,
        probe_health_fn=_probe_health,
    )


def _create_activity_tracker(log_path):
    return unity_session_wait.create_activity_tracker(
        log_path,
        read_editor_log_size_fn=_read_editor_log_size,
        time_ref=time,
    )


def _update_activity_tracker(activity_tracker, log_path):
    return unity_session_wait.update_activity_tracker(
        activity_tracker,
        log_path,
        read_editor_log_size_fn=_read_editor_log_size,
        time_ref=time,
    )


def _build_activity_state(activity_tracker):
    return unity_session_wait.build_activity_state(activity_tracker)


def _finalize_session_diagnostics(session, log_path, health_error, activity_tracker, last_payload=None):
    return unity_session_wait.finalize_session_diagnostics(
        session,
        log_path,
        health_error,
        activity_tracker,
        last_payload=last_payload,
        collect_diagnostics_fn=_collect_diagnostics,
    )


def _build_health_snapshot(payload, error):
    return unity_session_wait.build_health_snapshot(payload, error)


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
    return unity_session_wait.wait_for_session(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        completion_predicate=completion_predicate,
        timeout_message=timeout_message,
        iteration_observer=iteration_observer,
        default_editor_log_path_fn=_default_editor_log_path,
        probe_health_fn=_probe_health,
        create_activity_tracker_fn=_create_activity_tracker,
        update_activity_tracker_fn=_update_activity_tracker,
        finalize_session_diagnostics_fn=_finalize_session_diagnostics,
        time_ref=time,
    )


def wait_until_healthy(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
):
    return unity_session_wait.wait_until_healthy(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        wait_for_session_fn=_wait_for_session,
    )


def wait_until_recovered(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    recoverable_statuses=RECOVERABLE_HEALTH_STATUSES,
):
    return unity_session_wait.wait_until_recovered(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        recoverable_statuses=recoverable_statuses,
        wait_for_session_fn=_wait_for_session,
    )


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
    return unity_session_wait.wait_for_log_pattern(
        session,
        pattern,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        start_offset=start_offset,
        extract_group=extract_group,
        extract_json_group=extract_json_group,
        expected_session_marker=expected_session_marker,
        default_editor_log_path_fn=_default_editor_log_path,
        probe_health_fn=_probe_health,
        create_activity_tracker_fn=_create_activity_tracker,
        update_activity_tracker_fn=_update_activity_tracker,
        finalize_session_diagnostics_fn=_finalize_session_diagnostics,
        read_editor_log_size_fn=_read_editor_log_size,
        read_editor_log_chunk_fn=_read_editor_log_chunk,
        time_ref=time,
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

    return unity_session_process.ensure_stopped(
        project_path=project_path,
        mode=mode,
        timeout_seconds=timeout_seconds,
        resolve_project_path_fn=resolve_project_path,
        read_session_artifact_fn=read_session_artifact,
        session_artifact_path_fn=_session_artifact_path,
        list_unity_pids_fn=_list_unity_pids,
        is_pid_running_fn=_is_pid_running,
        default_base_url=direct_exec_client.DEFAULT_BASE_URL,
        time_ref=time,
    )


def close_session(session, keep_unity=False):
    return unity_session_process.close_session(session, keep_unity=keep_unity, is_pid_running_fn=_is_pid_running)

