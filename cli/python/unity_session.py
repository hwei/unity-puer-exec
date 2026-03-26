#!/usr/bin/env python3
import os
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
    PROJECT_RECOVERY_WINDOW_SECONDS,
    DEFAULT_READY_TIMEOUT_SECONDS,
    DEFAULT_STOP_TIMEOUT_SECONDS,
    ENV_FILE_NAME,
    POLL_INTERVAL_SECONDS,
    RECOVERABLE_HEALTH_STATUSES,
    SESSION_RELATIVE_PATH,
    UNITY_PROJECT_PATH_ENV,
    UnityLaunchConflictError,
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


def _launch_claim_path(project_path):
    return unity_session_logs.launch_claim_path(project_path)


def _unity_lockfile_path(project_path):
    return unity_session_logs.unity_lockfile_path(project_path)


def _pending_exec_artifact_path(project_path, request_id):
    return unity_session_logs.pending_exec_artifact_path(project_path, request_id)


def read_session_artifact(project_path):
    return unity_session_logs.read_session_artifact(project_path)


def read_launch_claim(project_path):
    return unity_session_logs.read_launch_claim(project_path)


def write_session_artifact(project_path, payload):
    return unity_session_logs.write_session_artifact(project_path, payload)


def write_launch_claim(project_path, payload):
    return unity_session_logs.write_launch_claim(project_path, payload)


def clear_launch_claim(project_path):
    return unity_session_logs.clear_launch_claim(project_path)


def read_pending_exec_artifact(project_path, request_id):
    return unity_session_logs.read_pending_exec_artifact(project_path, request_id)


def write_pending_exec_artifact(project_path, request_id, payload):
    return unity_session_logs.write_pending_exec_artifact(project_path, request_id, payload)


def clear_pending_exec_artifact(project_path, request_id):
    return unity_session_logs.clear_pending_exec_artifact(project_path, request_id)


def sweep_pending_exec_artifacts(project_path):
    return unity_session_logs.sweep_pending_exec_artifacts(project_path)


def _session_artifact_log_path(session_data):
    return unity_session_logs.session_artifact_log_path(session_data, is_pid_running_fn=_is_pid_running)


def _project_lock_details(project_path):
    return unity_session_logs.build_project_lock_details(project_path, time_ref=time)


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


def _artifact_pid_running(session_data):
    artifact_pid = None if not isinstance(session_data, dict) else session_data.get("unity_pid")
    if artifact_pid is None:
        return None, False
    return artifact_pid, _is_pid_running(artifact_pid)


def _build_launch_coordination_diagnostics(
    project_path,
    session_data,
    project_lock,
    launch_claim,
    unity_pids,
    artifact_pid,
    artifact_pid_running,
    stage,
):
    diagnostics = {
        "launch_coordination_stage": stage,
        "session_artifact_exists": session_data is not None,
        "project_lock_path": project_lock.get("path"),
        "project_lock_exists": project_lock.get("exists", False),
        "project_lock_fresh": project_lock.get("fresh", False),
        "launch_claim_path": str(_launch_claim_path(project_path)),
    }
    if artifact_pid is not None:
        diagnostics["session_artifact_pid"] = artifact_pid
        diagnostics["session_artifact_pid_running"] = artifact_pid_running
    if "age_seconds" in project_lock:
        diagnostics["project_lock_age_seconds"] = project_lock["age_seconds"]
    if isinstance(launch_claim, dict):
        diagnostics["launch_claim"] = dict(launch_claim)
    if unity_pids is not None:
        diagnostics["unity_pids"] = unity_pids
    return diagnostics


def _build_recovery_session(project_path, base_url, log_path, session_data, unity_pids, owner):
    artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)
    unity_pid = artifact_pid if artifact_pid_running else (unity_pids[0] if unity_pids else None)
    return UnitySession(
        owner=owner,
        base_url=base_url,
        project_path=project_path,
        unity_pid=unity_pid,
        launched=False,
        effective_log_path=log_path,
    )


def _has_recoverable_editor_signal(artifact_pid_running, unity_pids):
    return bool(artifact_pid_running or unity_pids)


def _build_ready_service_session(project_path, base_url, log_path, unity_pids, owner="existing_service"):
    return UnitySession(
        owner=owner,
        base_url=base_url,
        project_path=project_path,
        unity_pid=unity_pids[0] if unity_pids else None,
        launched=False,
        effective_log_path=log_path,
    )


def _raise_launch_conflict(project_path, base_url, log_path, error, session_data, project_lock, launch_claim, unity_pids, reason):
    artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)
    session = UnitySession(
        owner="launch_conflict",
        base_url=base_url,
        project_path=project_path,
        unity_pid=artifact_pid if artifact_pid_running else None,
        launched=False,
        effective_log_path=log_path,
    )
    session.diagnostics = _collect_diagnostics(base_url, log_path, error)
    session.diagnostics.update(
        _build_launch_coordination_diagnostics(
            project_path,
            session_data,
            project_lock,
            launch_claim,
            unity_pids,
            artifact_pid,
            artifact_pid_running,
            "conflict",
        )
    )
    session.diagnostics["launch_conflict_reason"] = reason
    raise UnityLaunchConflictError("launch ownership for the target project is not safely available", session=session)


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
        project_lock = _project_lock_details(project_path)
        launch_claim = read_launch_claim(project_path)
        artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)
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
        session.diagnostics.update(
            _build_launch_coordination_diagnostics(
                project_path,
                session_data,
                project_lock,
                launch_claim,
                initial_pids,
                artifact_pid,
                artifact_pid_running,
                "initial_ready",
            )
        )
        _persist_ready_session_artifact(session, log_path, payload=payload)
        return session

    project_lock = _project_lock_details(project_path)
    launch_claim = read_launch_claim(project_path)
    artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)
    claim_owner_pid = None if not isinstance(launch_claim, dict) else launch_claim.get("owner_pid")
    claim_active = claim_owner_pid not in (None, os.getpid()) and _is_pid_running(claim_owner_pid)

    if claim_active:
        _raise_launch_conflict(
            project_path,
            base_url,
            log_path,
            error,
            session_data,
            project_lock,
            launch_claim,
            initial_pids,
            "project_launch_claim_active",
        )

    if _has_recoverable_editor_signal(artifact_pid_running, initial_pids):
        owner = "session_artifact" if artifact_pid_running else "project_recovery"
        session = _build_recovery_session(project_path, base_url, log_path, session_data, initial_pids, owner)
        session.diagnostics = _collect_diagnostics(base_url, log_path, error)
        session.diagnostics.update(
            _build_launch_coordination_diagnostics(
                project_path,
                session_data,
                project_lock,
                launch_claim,
                initial_pids,
                artifact_pid,
                artifact_pid_running,
                "prelaunch_recovery",
            )
        )
        session = wait_ready_with_activity(
            session,
            ready_timeout_seconds,
            activity_timeout_seconds=activity_timeout_seconds,
            health_timeout_seconds=health_timeout_seconds,
            log_path=log_path,
        )
        _persist_ready_session_artifact(session, log_path)
        return _detach_session_process(session)

    claim_payload = {
        "owner_pid": os.getpid(),
        "created_at": time.time(),
        "recovery_window_seconds": PROJECT_RECOVERY_WINDOW_SECONDS,
    }
    write_launch_claim(project_path, claim_payload)
    try:
        followup_pids = _list_unity_pids()
        followup_payload, followup_error = _probe_health(base_url, health_timeout_seconds)
        followup_lock = _project_lock_details(project_path)
        artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)

        if followup_payload is not None and followup_payload.get("ok") and followup_payload.get("status") == "ready":
            session = _build_ready_service_session(project_path, base_url, log_path, followup_pids)
            if artifact_pid_running:
                session.unity_pid = artifact_pid
            activity_state = {
                "last_log_size": _read_editor_log_size(log_path),
                "last_activity_time": _format_wall_time(time.time()),
                "idle_seconds": 0.0,
            }
            session.diagnostics = _collect_diagnostics(base_url, log_path, None, activity_state)
            session.diagnostics["last_health_payload"] = followup_payload
            session.diagnostics.update(
                _build_launch_coordination_diagnostics(
                    project_path,
                    session_data,
                    followup_lock,
                    claim_payload,
                    followup_pids,
                    artifact_pid,
                    artifact_pid_running,
                    "post_claim_ready",
                )
            )
            _persist_ready_session_artifact(session, log_path, payload=followup_payload)
            return session

        if _has_recoverable_editor_signal(artifact_pid_running, followup_pids):
            owner = "session_artifact" if artifact_pid_running else "project_recovery"
            session = _build_recovery_session(project_path, base_url, log_path, session_data, followup_pids, owner)
            session.diagnostics = _collect_diagnostics(base_url, log_path, followup_error)
            session.diagnostics.update(
                _build_launch_coordination_diagnostics(
                    project_path,
                    session_data,
                    followup_lock,
                    claim_payload,
                    followup_pids,
                    artifact_pid,
                    artifact_pid_running,
                    "post_claim_recovery",
                )
            )
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
        session.diagnostics = _collect_diagnostics(base_url, log_path, followup_error or error)
        session.diagnostics.update(
            _build_launch_coordination_diagnostics(
                project_path,
                session_data,
                followup_lock,
                claim_payload,
                followup_pids,
                artifact_pid,
                artifact_pid_running,
                "launch_attempted",
            )
        )
        try:
            session = wait_ready_with_activity(
                session,
                ready_timeout_seconds,
                activity_timeout_seconds=activity_timeout_seconds,
                health_timeout_seconds=health_timeout_seconds,
                log_path=log_path,
            )
        except UnityLaunchError as exc:
            if exc.session is session and session.process is not None and session.process.returncode == 0:
                recovery_pids = _list_unity_pids()
                recovery_payload, recovery_error = _probe_health(base_url, health_timeout_seconds)
                recovery_lock = _project_lock_details(project_path)
                artifact_pid, artifact_pid_running = _artifact_pid_running(session_data)
                if recovery_payload is not None and recovery_payload.get("ok") and recovery_payload.get("status") == "ready":
                    session = _build_ready_service_session(project_path, base_url, log_path, recovery_pids, owner="recovered_service")
                    if artifact_pid_running:
                        session.unity_pid = artifact_pid
                    activity_state = {
                        "last_log_size": _read_editor_log_size(log_path),
                        "last_activity_time": _format_wall_time(time.time()),
                        "idle_seconds": 0.0,
                    }
                    session.diagnostics = _collect_diagnostics(base_url, log_path, None, activity_state)
                    session.diagnostics["last_health_payload"] = recovery_payload
                    session.diagnostics.update(
                        _build_launch_coordination_diagnostics(
                            project_path,
                            session_data,
                            recovery_lock,
                            claim_payload,
                            recovery_pids,
                            artifact_pid,
                            artifact_pid_running,
                            "post_launch_exit_ready",
                        )
                    )
                    _persist_ready_session_artifact(session, log_path, payload=recovery_payload)
                    return session
                if _has_recoverable_editor_signal(artifact_pid_running, recovery_pids):
                    recovery_session = _build_recovery_session(
                        project_path,
                        base_url,
                        log_path,
                        session_data,
                        recovery_pids,
                        "project_recovery",
                    )
                    recovery_session.diagnostics = _collect_diagnostics(base_url, log_path, recovery_error)
                    recovery_session.diagnostics.update(
                        _build_launch_coordination_diagnostics(
                            project_path,
                            session_data,
                            recovery_lock,
                            claim_payload,
                            recovery_pids,
                            artifact_pid,
                            artifact_pid_running,
                            "post_launch_exit_recovery",
                        )
                    )
                    recovery_session = wait_ready_with_activity(
                        recovery_session,
                        ready_timeout_seconds,
                        activity_timeout_seconds=activity_timeout_seconds,
                        health_timeout_seconds=health_timeout_seconds,
                        log_path=log_path,
                    )
                    _persist_ready_session_artifact(recovery_session, log_path)
                    return _detach_session_process(recovery_session)
            raise
        _persist_ready_session_artifact(session, log_path)
        return _detach_session_process(session)
    finally:
        current_claim = read_launch_claim(project_path)
        if isinstance(current_claim, dict) and current_claim.get("owner_pid") == os.getpid():
            clear_launch_claim(project_path)


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


def get_blocker_state(project_path=None):
    resolved_project_path = resolve_project_path(project_path)
    session_data = read_session_artifact(resolved_project_path)
    unity_pid = None
    owner = "blocker_observation"
    if session_data is not None:
        owner = "session_artifact"
        unity_pid = session_data.get("unity_pid")
        if unity_pid is not None and not _is_pid_running(unity_pid):
            unity_pid = None

    session = UnitySession(
        owner=owner,
        base_url=direct_exec_client.DEFAULT_BASE_URL,
        project_path=resolved_project_path,
        unity_pid=unity_pid,
        launched=False,
    )
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
