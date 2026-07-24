#!/usr/bin/env python3
import os
import time
from pathlib import Path

import cli_version
import direct_exec_client
import unity_session_endpoint
import unity_session_env
import unity_session_logs
import unity_session_process
import unity_session_wait
from unity_session_common import (
    COMPILE_APPEAR_POLL_INTERVAL_SECONDS,
    DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS,
    DEFAULT_EDITOR_LOG_MAX_LINES,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    PROJECT_RECOVERY_WINDOW_SECONDS,
    DEFAULT_READY_TIMEOUT_SECONDS,
    DEFAULT_STOP_TIMEOUT_SECONDS,
    ENV_FILE_NAME,
    POLL_INTERVAL_SECONDS,
    RECOVERABLE_HEALTH_STATUSES,
    SERVICE_RESTART_GRACE_SECONDS,
    UNITY_PROJECT_PATH_ENV,
    UnityEditorNotUnderControlError,
    UnityLaunchConflictError,
    UnityLaunchError,
    UnityNotReadyError,
    UnitySession,
    UnitySessionError,
    UnitySessionStateError,
    UnityStalledError,
    UnityVersionMismatchError,
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


def resolve_project_path(project_path=None, cwd=None, env=None, argv0=None):
    return unity_session_env.resolve_project_path(
        __file__,
        project_path=project_path,
        cwd=cwd,
        env=env,
        ensure_dotenv_loaded_fn=_ensure_dotenv_loaded,
        argv0=argv0,
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


def _project_lockfile_is_held(project_path):
    return unity_session_process._project_lockfile_is_held(project_path)


def _probe_health(base_url, timeout_seconds):
    return unity_session_wait.probe_health(base_url, timeout_seconds)


def _endpoint_publication_path(project_path):
    return unity_session_endpoint.endpoint_publication_path(project_path)


def read_endpoint_publication(project_path):
    return unity_session_endpoint.read_endpoint_publication(project_path, time_ref=time)


def classify_session_state(project_path, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS, grace_seconds=SERVICE_RESTART_GRACE_SECONDS):
    """Answer 'what is serving this project, and can I drive it' from local files."""
    return unity_session_endpoint.classify_session_state(
        project_path,
        lockfile_held_fn=_project_lockfile_is_held,
        read_publication_fn=read_endpoint_publication,
        probe_health_fn=_probe_health,
        health_timeout_seconds=health_timeout_seconds,
        is_pid_running_fn=_is_pid_running,
        grace_seconds=grace_seconds,
        time_ref=time,
    )


def _launch_claim_path(project_path):
    return unity_session_logs.launch_claim_path(project_path)


def _unity_lockfile_path(project_path):
    return unity_session_logs.unity_lockfile_path(project_path)


def _pending_exec_artifact_path(project_path, request_id):
    return unity_session_logs.pending_exec_artifact_path(project_path, request_id)


def read_launch_claim(project_path):
    return unity_session_logs.read_launch_claim(project_path)


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


def _project_lock_details(project_path):
    return unity_session_logs.build_project_lock_details(project_path, time_ref=time)


def _resolve_effective_log_path_with_tier(project_path, unity_log_path=None, publication=None, health_console_log_path=None):
    return unity_session_logs.resolve_effective_log_path_with_tier(
        project_path,
        unity_log_path=unity_log_path,
        publication=publication,
        health_console_log_path=health_console_log_path,
        read_endpoint_publication_fn=read_endpoint_publication,
        default_editor_log_path_fn=_default_editor_log_path,
    )


def _resolve_effective_log_path(project_path, unity_log_path=None, publication=None, health_console_log_path=None):
    path, _tier = _resolve_effective_log_path_with_tier(
        project_path,
        unity_log_path=unity_log_path,
        publication=publication,
        health_console_log_path=health_console_log_path,
    )
    return path


def _health_console_log_path(payload):
    return unity_session_logs.health_console_log_path(payload)


def _probe_console_log_path(project_path, publication=None, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS):
    """Ask a reachable, project-owned endpoint where its Editor writes.

    Only reached when the project published nothing, so it is an error-path
    diagnostic rather than the normal way to find a log. Observation-only, so it
    deliberately does not run the bridge-version guard the launch paths use:
    locating a log must not start refusing work. An endpoint owned by a different
    project is never adopted -- its log path names the wrong file, which is the
    exact failure this tier exists to remove.
    """
    candidates = []
    if isinstance(publication, dict):
        published_base_url = publication.get("base_url")
        if isinstance(published_base_url, str) and published_base_url:
            candidates.append(published_base_url)
    for candidate in direct_exec_client.candidate_base_urls():
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        payload, _error = _probe_health(candidate, health_timeout_seconds)
        if payload is None or not payload.get("ok") or payload.get("status") != "ready":
            continue
        if not _payload_matches_project(payload, project_path):
            continue
        return _health_console_log_path(payload)
    return None


def _log_path_from_ready_payload(project_path, unity_log_path, publication, payload, current_log_path):
    """Re-resolve the observed log once a ready endpoint has stated where it writes.

    Only the tier that was previously a platform-default guess can change here;
    an explicit flag or the Editor's own publication still outranks the statement.
    """
    reported = _health_console_log_path(payload)
    if reported is None:
        return current_log_path
    return _resolve_effective_log_path(
        project_path,
        unity_log_path=unity_log_path,
        publication=publication,
        health_console_log_path=reported,
    )


def _session_marker_from_payload(payload):
    return unity_session_logs.session_marker_from_payload(payload)


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


def _prepare_launch_log_path(project_path, unity_log_path=None):
    return unity_session_logs.prepare_launch_log_path(project_path, unity_log_path=unity_log_path)


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


def _published_pid_running(publication):
    """Liveness of the process the project's own Editor named.

    Distinct from the removed artifact's pid check in the only way that matters:
    this pid was stated by the Editor about itself, so it cannot be a different
    project's Editor that merely happened to sort first in the machine-wide
    tasklist. It is still never the sole evidence that a session is live -- the
    project lockfile carries that -- so a recycled pid cannot resurrect one.
    """
    published_pid = None if not isinstance(publication, dict) else publication.get("unity_pid")
    if published_pid is None:
        return None, False
    return published_pid, _is_pid_running(published_pid)


def _session_pid_from_sources(payload, publication):
    """Pick the session's process id from what the Editor said, or nothing at all.

    Previously this fell back to ``list_unity_pids()[0]`` -- the first Unity.exe in
    the machine-wide tasklist -- which on a machine with several projects open
    recorded an unrelated project's pid and then drove recovery signalling,
    launch-conflict detection, and `ensure-stopped --immediate-kill`. There is no
    fallback now: an unknown pid is reported as unknown.
    """
    if isinstance(payload, dict):
        reported = payload.get("unity_pid")
        if isinstance(reported, int) and reported > 0:
            return reported
    if isinstance(publication, dict):
        published = publication.get("unity_pid")
        if isinstance(published, int) and published > 0:
            return published
    return None


def _build_launch_coordination_diagnostics(
    project_path,
    publication,
    project_lock,
    launch_claim,
    unity_pids,
    published_pid,
    published_pid_running,
    stage,
):
    diagnostics = {
        "launch_coordination_stage": stage,
        "endpoint_publication_exists": publication is not None,
        "endpoint_publication_path": str(_endpoint_publication_path(project_path)),
        "project_lock_path": project_lock.get("path"),
        "project_lock_exists": project_lock.get("exists", False),
        "project_lock_fresh": project_lock.get("fresh", False),
        "launch_claim_path": str(_launch_claim_path(project_path)),
    }
    if published_pid is not None:
        diagnostics["published_unity_pid"] = published_pid
        diagnostics["published_unity_pid_running"] = published_pid_running
    if "age_seconds" in project_lock:
        diagnostics["project_lock_age_seconds"] = project_lock["age_seconds"]
    if isinstance(launch_claim, dict):
        diagnostics["launch_claim"] = dict(launch_claim)
    # Retained as a diagnostic only. Nothing decides anything from it: a
    # machine-wide count cannot answer a per-project question.
    if unity_pids is not None:
        diagnostics["unity_pids"] = unity_pids
    return diagnostics


def _build_recovery_session(project_path, base_url, log_path, publication, owner):
    published_pid, published_pid_running = _published_pid_running(publication)
    return UnitySession(
        owner=owner,
        base_url=base_url,
        project_path=project_path,
        unity_pid=published_pid if published_pid_running else None,
        launched=False,
        effective_log_path=log_path,
    )


def _has_recoverable_editor_signal(published_pid_running, project_path):
    return bool(published_pid_running or _project_lockfile_is_held(project_path))


def _build_ready_service_session(project_path, base_url, log_path, publication, payload=None, owner="existing_service"):
    return UnitySession(
        owner=owner,
        base_url=base_url,
        project_path=project_path,
        unity_pid=_session_pid_from_sources(payload, publication),
        launched=False,
        effective_log_path=log_path,
    )


def _raise_launch_conflict(project_path, base_url, log_path, error, publication, project_lock, launch_claim, unity_pids, reason):
    published_pid, published_pid_running = _published_pid_running(publication)
    session = UnitySession(
        owner="launch_conflict",
        base_url=base_url,
        project_path=project_path,
        unity_pid=published_pid if published_pid_running else None,
        launched=False,
        effective_log_path=log_path,
    )
    session.diagnostics = _collect_diagnostics(base_url, log_path, error)
    session.diagnostics.update(
        _build_launch_coordination_diagnostics(
            project_path,
            publication,
            project_lock,
            launch_claim,
            unity_pids,
            published_pid,
            published_pid_running,
            "conflict",
        )
    )
    session.diagnostics["launch_conflict_reason"] = reason
    raise UnityLaunchConflictError("launch ownership for the target project is not safely available", session=session)


def _raise_editor_not_under_control(
    project_path,
    log_path,
    publication,
    project_lock,
    launch_claim,
    unity_pids,
    health_timeout_seconds,
):
    """Refuse a running Editor that never activated a control service, and say so usefully.

    The error path is the one place the control-port scan still earns its keep. An
    Editor running an older bridge starts its service implicitly, publishes nothing,
    and has no activation menu item -- so guidance that said "activate it from the
    Editor menu" would point at something that bridge does not have. Scanning here
    finds such a service, and its version disagreement is reported as
    `version_mismatch` instead, pointing the caller at aligning the installation.
    The scan's cost is paid only when the command is already failing.
    """
    published_pid, published_pid_running = _published_pid_running(publication)
    session = UnitySession(
        owner="editor_not_under_cli_control",
        base_url=direct_exec_client.DEFAULT_BASE_URL,
        project_path=project_path,
        unity_pid=published_pid if published_pid_running else None,
        launched=False,
        effective_log_path=log_path,
    )
    session.diagnostics = _build_launch_coordination_diagnostics(
        project_path,
        publication,
        project_lock,
        launch_claim,
        unity_pids,
        published_pid,
        published_pid_running,
        "not_under_cli_control",
    )

    # Raises UnityVersionMismatchError from inside the identity guard when a
    # project-owned service answers with a version this CLI cannot match.
    scanned_base_url, payload, _error, saw_other_project = discover_project_endpoint(
        project_path,
        health_timeout_seconds,
    )
    session.diagnostics["error_path_scan_saw_other_project"] = saw_other_project
    if payload is not None:
        # A same-version service that answers but published nothing. Under this
        # design that is a failure mode rather than a supported third path, so it is
        # reported rather than adopted.
        session.diagnostics["error_path_scan_found_base_url"] = scanned_base_url

    guidance = [
        "Let the CLI launch the Editor, which grants both control and an isolated log.",
        "Or activate the service in the running Editor: {}.".format(
            "Tools/UnityPuerExec/Activate CLI Control (this session)"
        ),
        "Mid-session activation grants control but not log isolation, because a Unity "
        "process binds its log at startup.",
    ]
    session.diagnostics["guidance"] = guidance
    raise UnityEditorNotUnderControlError(
        "an Editor is running for this project but has not activated a CLI control service",
        session=session,
        guidance=guidance,
    )


def _make_published_endpoint_resolver(project_path, health_timeout_seconds):
    """Keep a wait loop pointed at whatever this project currently publishes.

    Replaces the control-port scan on the readiness path. An Editor publishes as
    soon as it binds and republishes after every domain reload, so re-reading the
    publication follows a rolled-over port without ever probing a port that does not
    belong to this project.
    """

    def resolve():
        publication = read_endpoint_publication(project_path)
        if publication is None:
            return None
        base_url = publication["base_url"]
        payload, _error = _probe_health(base_url, health_timeout_seconds)
        if payload is None or payload.get("session_marker") != publication["session_marker"]:
            return None
        # Pre-ready payloads carry no version yet, so an absent bridge_version here
        # is "not observable yet", not a mismatch.
        _guard_owned_endpoint_version(base_url, payload, require_version=False)
        return base_url

    return resolve


def _wait_for_session(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    completion_predicate=None,
    timeout_message=None,
    iteration_observer=None,
    endpoint_resolver=None,
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
        endpoint_resolver=endpoint_resolver,
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
    endpoint_resolver=None,
):
    return unity_session_wait.wait_until_healthy(
        session,
        timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        endpoint_resolver=endpoint_resolver,
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
    endpoint_resolver=None,
):
    return wait_until_healthy(
        session,
        ready_timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        log_path=log_path,
        endpoint_resolver=endpoint_resolver,
    )


def ensure_session_ready(
    project_path=None,
    base_url=direct_exec_client.DEFAULT_BASE_URL,
    unity_exe_path=None,
    ready_timeout_seconds=DEFAULT_READY_TIMEOUT_SECONDS,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    unity_log_path=None,
    argv0=None,
):
    """Prepare a ready project session, refusing a bridge this CLI cannot match.

    The launch and recovery paths lock onto the project's port through pre-`ready`
    payloads, which carry no identity fields yet, so the version can only be
    required once the endpoint is actually ready. That is here -- after readiness,
    before the caller executes anything.
    """
    session = _ensure_session_ready_unguarded(
        project_path=project_path,
        base_url=base_url,
        unity_exe_path=unity_exe_path,
        ready_timeout_seconds=ready_timeout_seconds,
        activity_timeout_seconds=activity_timeout_seconds,
        health_timeout_seconds=health_timeout_seconds,
        unity_log_path=unity_log_path,
        argv0=argv0,
    )
    payload, error = _probe_health(session.base_url, health_timeout_seconds)
    if payload is not None and error is None:
        _guard_owned_endpoint_version(session.base_url, payload)
    return session


def _ensure_session_ready_unguarded(
    project_path=None,
    base_url=direct_exec_client.DEFAULT_BASE_URL,
    unity_exe_path=None,
    ready_timeout_seconds=DEFAULT_READY_TIMEOUT_SECONDS,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    unity_log_path=None,
    argv0=None,
):
    project_path = resolve_project_path(project_path, argv0=argv0)
    # Diagnostic only. Nothing below decides anything from this list -- deriving a
    # project's session identity from machine-wide tasklist order is the defect this
    # change removes.
    initial_pids = _list_unity_pids()
    error = None

    # Two project-local files decide the whole state space: the project's Unity
    # lockfile and the endpoint its own Editor published. No control-port scan and
    # no process-table correlation participate, so an Editor open on an unrelated
    # project cannot influence the answer for this one.
    state, publication, health_payload = classify_session_state(
        project_path,
        health_timeout_seconds=health_timeout_seconds,
    )
    log_path = _resolve_effective_log_path(project_path, unity_log_path=unity_log_path, publication=publication)
    published_pid, published_pid_running = _published_pid_running(publication)
    project_lock = _project_lock_details(project_path)
    launch_claim = read_launch_claim(project_path)

    if state == unity_session_endpoint.SESSION_STATE_NOT_UNDER_CONTROL:
        _raise_editor_not_under_control(
            project_path,
            log_path,
            publication,
            project_lock,
            launch_claim,
            initial_pids,
            health_timeout_seconds,
        )

    if state == unity_session_endpoint.SESSION_STATE_CONTROLLED:
        base_url = publication["base_url"]
        if health_payload is not None and health_payload.get("ok") and health_payload.get("status") == "ready":
            # One direct connection, to the port the Editor itself named. The
            # 19-port scan is gone from this path entirely.
            log_path = _log_path_from_ready_payload(project_path, unity_log_path, publication, health_payload, log_path)
            session = _build_ready_service_session(
                project_path,
                base_url,
                log_path,
                publication,
                payload=health_payload,
                owner="published_endpoint",
            )
            activity_state = {
                "last_log_size": _read_editor_log_size(log_path),
                "last_activity_time": _format_wall_time(time.time()),
                "idle_seconds": 0.0,
            }
            session.diagnostics = _collect_diagnostics(base_url, log_path, None, activity_state)
            session.diagnostics["last_health_payload"] = health_payload
            session.diagnostics.update(
                _build_launch_coordination_diagnostics(
                    project_path,
                    publication,
                    project_lock,
                    launch_claim,
                    initial_pids,
                    published_pid,
                    published_pid_running,
                    "published_endpoint_ready",
                )
            )
            return session

        # Controlled, but not ready yet: compiling, reloading, or a service
        # restarting across a domain reload. Waiting is what the readiness loop is
        # for, and it stays pinned to the publication rather than scanning.
        session = _build_recovery_session(project_path, base_url, log_path, publication, "published_endpoint_recovery")
        session.diagnostics = _collect_diagnostics(base_url, log_path, None)
        session.diagnostics.update(
            _build_launch_coordination_diagnostics(
                project_path,
                publication,
                project_lock,
                launch_claim,
                initial_pids,
                published_pid,
                published_pid_running,
                "published_endpoint_recovery",
            )
        )
        session = wait_ready_with_activity(
            session,
            ready_timeout_seconds,
            activity_timeout_seconds=activity_timeout_seconds,
            health_timeout_seconds=health_timeout_seconds,
            log_path=log_path,
            endpoint_resolver=_make_published_endpoint_resolver(project_path, health_timeout_seconds),
        )
        return _detach_session_process(session)

    # Remaining states are "no Editor" and "residue from an Editor that crashed or
    # was killed". Nothing is serving the project in either, so a launch may proceed;
    # a residue publication names a port that is gone and is not adopted.
    claim_owner_pid = None if not isinstance(launch_claim, dict) else launch_claim.get("owner_pid")
    claim_active = claim_owner_pid not in (None, os.getpid()) and _is_pid_running(claim_owner_pid)

    if claim_active:
        _raise_launch_conflict(
            project_path,
            base_url,
            log_path,
            error,
            publication,
            project_lock,
            launch_claim,
            initial_pids,
            "project_launch_claim_active",
        )

    claim_payload = {
        "owner_pid": os.getpid(),
        "created_at": time.time(),
        "recovery_window_seconds": PROJECT_RECOVERY_WINDOW_SECONDS,
    }
    write_launch_claim(project_path, claim_payload)
    try:
        followup_pids = _list_unity_pids()
        # Re-decide under the claim: between the first reading and here, a human
        # could have opened the project, or a concurrently launching Editor could
        # have finished binding.
        followup_state, followup_publication, followup_payload = classify_session_state(
            project_path,
            health_timeout_seconds=health_timeout_seconds,
        )
        followup_lock = _project_lock_details(project_path)
        followup_pid, followup_pid_running = _published_pid_running(followup_publication)

        if followup_state == unity_session_endpoint.SESSION_STATE_NOT_UNDER_CONTROL:
            _raise_editor_not_under_control(
                project_path,
                log_path,
                followup_publication,
                followup_lock,
                claim_payload,
                followup_pids,
                health_timeout_seconds,
            )

        if followup_state == unity_session_endpoint.SESSION_STATE_CONTROLLED:
            base_url = followup_publication["base_url"]
            if followup_payload is not None and followup_payload.get("ok") and followup_payload.get("status") == "ready":
                log_path = _log_path_from_ready_payload(project_path, unity_log_path, followup_publication, followup_payload, log_path)
                session = _build_ready_service_session(
                    project_path,
                    base_url,
                    log_path,
                    followup_publication,
                    payload=followup_payload,
                    owner="published_endpoint",
                )
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
                        followup_publication,
                        followup_lock,
                        claim_payload,
                        followup_pids,
                        followup_pid,
                        followup_pid_running,
                        "post_claim_ready",
                    )
                )
                return session

            session = _build_recovery_session(
                project_path,
                base_url,
                log_path,
                followup_publication,
                "published_endpoint_recovery",
            )
            session.diagnostics = _collect_diagnostics(base_url, log_path, None)
            session.diagnostics.update(
                _build_launch_coordination_diagnostics(
                    project_path,
                    followup_publication,
                    followup_lock,
                    claim_payload,
                    followup_pids,
                    followup_pid,
                    followup_pid_running,
                    "post_claim_recovery",
                )
            )
            session = wait_ready_with_activity(
                session,
                ready_timeout_seconds,
                activity_timeout_seconds=activity_timeout_seconds,
                health_timeout_seconds=health_timeout_seconds,
                log_path=log_path,
                endpoint_resolver=_make_published_endpoint_resolver(project_path, health_timeout_seconds),
            )
            return _detach_session_process(session)

        resolved_unity_exe_path = _resolve_unity_exe_path(project_path, unity_exe_path)
        # An Editor this CLI starts gets a project-private log, so an unrelated
        # Editor cannot share, rotate, or truncate the file this session is
        # observed through. It also gets the activation switch, because the control
        # service no longer starts on its own. The launched Editor publishes both
        # the port and the same log path back, so later commands need no flags.
        launch_log_path = _prepare_launch_log_path(project_path, unity_log_path)
        process = _launch_unity(project_path, resolved_unity_exe_path, unity_log_path=launch_log_path)
        log_path = launch_log_path
        # Cold start: any residue publication names a service that is gone. The
        # endpoint the new Editor publishes is the only source of truth.
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
        session.diagnostics.update(
            _build_launch_coordination_diagnostics(
                project_path,
                followup_publication,
                followup_lock,
                claim_payload,
                followup_pids,
                followup_pid,
                followup_pid_running,
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
                endpoint_resolver=_make_published_endpoint_resolver(project_path, health_timeout_seconds),
            )
        except UnityLaunchError as exc:
            # The launcher process exited cleanly without this CLI reaching a ready
            # endpoint. Unity does that when it hands the project to an already
            # running Editor, so re-decide rather than reporting a launch failure.
            if exc.session is session and session.process is not None and session.process.returncode == 0:
                recovery_pids = _list_unity_pids()
                recovery_state, recovery_publication, recovery_payload = classify_session_state(
                    project_path,
                    health_timeout_seconds=health_timeout_seconds,
                )
                recovery_lock = _project_lock_details(project_path)
                recovery_pid, recovery_pid_running = _published_pid_running(recovery_publication)
                if recovery_state == unity_session_endpoint.SESSION_STATE_CONTROLLED:
                    base_url = recovery_publication["base_url"]
                    if recovery_payload is not None and recovery_payload.get("ok") and recovery_payload.get("status") == "ready":
                        log_path = _log_path_from_ready_payload(project_path, unity_log_path, recovery_publication, recovery_payload, log_path)
                        session = _build_ready_service_session(
                            project_path,
                            base_url,
                            log_path,
                            recovery_publication,
                            payload=recovery_payload,
                            owner="recovered_service",
                        )
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
                                recovery_publication,
                                recovery_lock,
                                claim_payload,
                                recovery_pids,
                                recovery_pid,
                                recovery_pid_running,
                                "post_launch_exit_ready",
                            )
                        )
                        return session

                    recovery_session = _build_recovery_session(
                        project_path,
                        base_url,
                        log_path,
                        recovery_publication,
                        "published_endpoint_recovery",
                    )
                    recovery_session.diagnostics = _collect_diagnostics(base_url, log_path, None)
                    recovery_session.diagnostics.update(
                        _build_launch_coordination_diagnostics(
                            project_path,
                            recovery_publication,
                            recovery_lock,
                            claim_payload,
                            recovery_pids,
                            recovery_pid,
                            recovery_pid_running,
                            "post_launch_exit_recovery",
                        )
                    )
                    recovery_session = wait_ready_with_activity(
                        recovery_session,
                        ready_timeout_seconds,
                        activity_timeout_seconds=activity_timeout_seconds,
                        health_timeout_seconds=health_timeout_seconds,
                        log_path=log_path,
                        endpoint_resolver=_make_published_endpoint_resolver(project_path, health_timeout_seconds),
                    )
                    return _detach_session_process(recovery_session)
                if recovery_state == unity_session_endpoint.SESSION_STATE_NOT_UNDER_CONTROL:
                    _raise_editor_not_under_control(
                        project_path,
                        log_path,
                        recovery_publication,
                        recovery_lock,
                        claim_payload,
                        recovery_pids,
                        health_timeout_seconds,
                    )
            raise
        return _detach_session_process(session)
    finally:
        current_claim = read_launch_claim(project_path)
        if isinstance(current_claim, dict) and current_claim.get("owner_pid") == os.getpid():
            clear_launch_claim(project_path)


def get_log_source(project_path=None, base_url=None, unity_log_path=None, argv0=None):
    resolved_project_path = resolve_project_path(project_path, argv0=argv0)
    if base_url is not None:
        payload, _error = _probe_health(base_url, DEFAULT_HEALTH_TIMEOUT_SECONDS)
        reported = _health_console_log_path(payload) if isinstance(payload, dict) and payload.get("status") == "ready" else None
        if reported:
            log_path = Path(reported)
            tier = unity_session_logs.LOG_SOURCE_TIER_CONTROL_SERVICE
        else:
            log_path = _default_editor_log_path()
            tier = unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT
    else:
        publication = read_endpoint_publication(resolved_project_path)
        log_path, tier = _resolve_effective_log_path_with_tier(
            resolved_project_path,
            unity_log_path=unity_log_path,
            publication=publication,
        )
        if tier == unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT:
            reported = _probe_console_log_path(resolved_project_path, publication)
            if reported:
                log_path, tier = _resolve_effective_log_path_with_tier(
                    resolved_project_path,
                    unity_log_path=unity_log_path,
                    publication=publication,
                    health_console_log_path=reported,
                )

    # A path an authority named -- a flag, an artifact, or the Editor itself --
    # is still the answer before the file appears on disk. Only the guess has to
    # prove itself by existing.
    if tier == unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT and not log_path.exists():
        return None

    session = UnitySession(
        owner="observation",
        base_url=(base_url or direct_exec_client.DEFAULT_BASE_URL),
        project_path=resolved_project_path,
        unity_pid=None,
        launched=False,
        effective_log_path=log_path,
    )
    return session, {
        "status": "log_source_available",
        "source": "file",
        "path": str(log_path),
        "resolution_tier": tier,
    }


def create_direct_session(base_url, project_path=None):
    return UnitySession(
        owner="direct_service",
        base_url=base_url,
        project_path=resolve_project_path(project_path),
        launched=False,
    )


def create_observation_session(project_path=None, base_url=None, unity_log_path=None, argv0=None):
    resolved_project_path = resolve_project_path(project_path, argv0=argv0)
    publication = read_endpoint_publication(resolved_project_path)
    unity_pid = None
    effective_base_url = base_url or direct_exec_client.DEFAULT_BASE_URL
    owner = "observation"
    # No control-service probe here: an observation session is built on the cold
    # path of every wait command, and the Editor's publication already answers the
    # question without one. get-log-source is where a caller asks directly and can
    # afford to pay for a probe.
    log_path = _resolve_effective_log_path(
        resolved_project_path,
        unity_log_path=unity_log_path,
        publication=publication,
    )
    if publication is not None:
        effective_base_url = publication.get("base_url") or effective_base_url
        unity_pid = publication.get("unity_pid")
        if publication.get("console_log_path"):
            owner = "published_endpoint"
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


def get_blocker_state(project_path=None, argv0=None):
    resolved_project_path = resolve_project_path(project_path, argv0=argv0)
    publication = read_endpoint_publication(resolved_project_path)
    unity_pid = None
    owner = "blocker_observation"
    if publication is not None:
        owner = "published_endpoint"
        unity_pid = publication.get("unity_pid")
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


def probe_health_payload(base_url, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS):
    """Public single health probe, used by the base-url bridge guard."""
    return _probe_health(base_url, health_timeout_seconds)


def _guard_owned_endpoint_version(base_url, payload, require_version=True):
    """Refuse an owned endpoint whose bridge version disagrees with this CLI.

    Called only where ownership has just been confirmed -- never on the foreign
    endpoints the control-port scan walks past -- so an unrelated project's Editor
    can never trigger a refusal here.
    """
    detail = cli_version.check_bridge(
        cli_version.resolve_cli_version(),
        base_url,
        payload,
        require_version=require_version,
    )
    if detail is not None:
        raise UnityVersionMismatchError(detail, message=cli_version.mismatch_message(detail))


def _payload_matches_project(payload, project_path):
    """Check whether a health payload belongs to the target project."""
    health_project_path = payload.get("project_path")
    if not isinstance(health_project_path, str) or not health_project_path:
        return False
    return os.path.normcase(os.path.normpath(health_project_path)) == os.path.normcase(os.path.normpath(str(project_path)))


def validate_endpoint_identity(base_url, project_path, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS):
    """Probe a candidate endpoint and verify it belongs to the target project.

    Returns (is_valid, payload, error).
    A valid endpoint is reachable, reports healthy status, and its health
    project_path matches the expected project_path.
    """
    payload, error = _probe_health(base_url, health_timeout_seconds)
    if payload is None:
        return False, None, error
    if not payload.get("ok") or payload.get("status") != "ready":
        return False, payload, None
    if not _payload_matches_project(payload, project_path):
        return False, payload, None
    _guard_owned_endpoint_version(base_url, payload)
    return True, payload, None


def discover_project_endpoint(project_path, health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS, candidate_base_urls=None):
    """Scan the control-port range for a ready endpoint owned by the target project.

    Candidates are probed in preferred-first order and the scan stops at the first
    ready endpoint whose health identity matches ``project_path``. A ready endpoint
    owned by a different project is never claimed; it only flips ``saw_other_project``
    so callers can distinguish "nothing answered" from "another project answered".

    Returns ``(base_url, payload, last_error, saw_other_project)`` where ``payload`` is
    ``None`` when no project-matched endpoint was found.
    """
    if candidate_base_urls is None:
        candidate_base_urls = direct_exec_client.candidate_base_urls()
    last_error = None
    saw_other_project = False
    for candidate in candidate_base_urls:
        is_valid, payload, error = validate_endpoint_identity(
            candidate,
            project_path,
            health_timeout_seconds=health_timeout_seconds,
        )
        if is_valid:
            return candidate, payload, None, saw_other_project
        if error is not None:
            last_error = error
        elif payload is not None and payload.get("ok") and payload.get("status") == "ready":
            saw_other_project = True
    return None, None, last_error, saw_other_project


def _scan_for_project_endpoint_any_status(project_path, health_timeout_seconds, candidate_base_urls=None):
    """Find a candidate whose health identity matches the project at any status.

    Unlike :func:`discover_project_endpoint`, this matches a starting, compiling, or
    reloading Editor that reports the target ``project_path`` but is not yet ``ready``,
    so a readiness wait can lock onto the actually-bound port before it goes ready.
    """
    if candidate_base_urls is None:
        candidate_base_urls = direct_exec_client.candidate_base_urls()
    for candidate in candidate_base_urls:
        payload, _error = _probe_health(candidate, health_timeout_seconds)
        if payload is not None and _payload_matches_project(payload, project_path):
            # Pre-ready payloads carry no identity fields yet, so an absent
            # bridge_version here is "not observable yet", not a mismatch.
            _guard_owned_endpoint_version(candidate, payload, require_version=False)
            return candidate
    return None


def _make_recovery_endpoint_resolver(project_path, health_timeout_seconds):
    """Build a stateful resolver that keeps a wait loop pointed at the project's port.

    While unlocked it scans the control-port range for a project-matched endpoint
    (any status). Once locked it re-probes only the locked port and re-scans solely
    if that port stops matching, so steady-state waiting stays a single probe per poll.
    """
    state = {"locked": None}

    def resolve():
        locked = state["locked"]
        if locked is not None:
            payload, _error = _probe_health(locked, health_timeout_seconds)
            if payload is not None and _payload_matches_project(payload, project_path):
                _guard_owned_endpoint_version(locked, payload, require_version=False)
                return locked
            state["locked"] = None
        found = _scan_for_project_endpoint_any_status(project_path, health_timeout_seconds)
        if found is not None:
            state["locked"] = found
        return found

    return resolve


def ensure_stopped(project_path=None, base_url=None, mode="inspect", timeout_seconds=DEFAULT_STOP_TIMEOUT_SECONDS, argv0=None):
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
        resolve_project_path_fn=lambda p: resolve_project_path(p, argv0=argv0),
        read_endpoint_publication_fn=read_endpoint_publication,
        endpoint_publication_path_fn=_endpoint_publication_path,
        lockfile_held_fn=_project_lockfile_is_held,
        is_pid_running_fn=_is_pid_running,
        default_base_url=direct_exec_client.DEFAULT_BASE_URL,
        time_ref=time,
    )


def close_session(session, keep_unity=False):
    return unity_session_process.close_session(session, keep_unity=keep_unity, is_pid_running_fn=_is_pid_running)
