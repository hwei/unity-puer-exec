#!/usr/bin/env python3
import json
import re
import time as time_module
from pathlib import Path

import direct_exec_client
from unity_session_common import (
    DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    DEFAULT_EDITOR_LOG_MAX_LINES,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    POLL_INTERVAL_SECONDS,
    RECOVERABLE_HEALTH_STATUSES,
    UnityLaunchError,
    UnityNotReadyError,
    UnitySessionStateError,
    UnityStalledError,
)


def format_wall_time(timestamp, time_ref=None):
    time_ref = time_module if time_ref is None else time_ref
    return time_ref.strftime("%Y-%m-%dT%H:%M:%S", time_ref.localtime(timestamp))


def probe_health(base_url, timeout_seconds):
    transport = direct_exec_client.HttpTransport()
    health_url = base_url.rstrip("/") + "/health"
    try:
        payload = transport.post_json(health_url, {}, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - dependency-free diagnostics.
        return None, str(exc)
    return payload, None


def collect_diagnostics(
    base_url,
    log_path,
    health_error,
    activity_state=None,
    health_payload=None,
    list_unity_pids_fn=None,
    read_recent_editor_log_lines_fn=None,
    probe_health_fn=None,
):
    diagnostics = {
        "unity_pids": list_unity_pids_fn(),
        "editor_log_path": str(log_path),
        "editor_log_exists": Path(log_path).exists(),
        "recent_editor_log_lines": read_recent_editor_log_lines_fn(log_path, DEFAULT_EDITOR_LOG_MAX_LINES),
    }
    if health_error is not None:
        diagnostics["last_health_error"] = health_error
    if health_payload is not None:
        diagnostics["last_health_payload"] = health_payload
    elif health_error is None:
        payload, _ = probe_health_fn(base_url, DEFAULT_HEALTH_TIMEOUT_SECONDS)
        if payload is not None:
            diagnostics["last_health_payload"] = payload
    if activity_state is not None:
        diagnostics["last_log_size"] = activity_state.get("last_log_size")
        diagnostics["last_activity_time"] = activity_state.get("last_activity_time")
        diagnostics["idle_seconds"] = activity_state.get("idle_seconds")
    return diagnostics


def create_activity_tracker(log_path, read_editor_log_size_fn=None, time_ref=None):
    time_ref = time_module if time_ref is None else time_ref
    now = time_ref.time()
    return {
        "last_log_size": read_editor_log_size_fn(log_path),
        "last_activity_monotonic": now,
        "last_activity_time": format_wall_time(now, time_ref=time_ref),
        "idle_seconds": 0.0,
    }


def update_activity_tracker(activity_tracker, log_path, read_editor_log_size_fn=None, time_ref=None):
    time_ref = time_module if time_ref is None else time_ref
    current_log_size = read_editor_log_size_fn(log_path)
    if current_log_size is not None and current_log_size != activity_tracker["last_log_size"]:
        now = time_ref.time()
        activity_tracker["last_log_size"] = current_log_size
        activity_tracker["last_activity_monotonic"] = now
        activity_tracker["last_activity_time"] = format_wall_time(now, time_ref=time_ref)

    activity_tracker["idle_seconds"] = round(
        max(0.0, time_ref.time() - activity_tracker["last_activity_monotonic"]),
        3,
    )
    return activity_tracker


def build_activity_state(activity_tracker):
    return {
        "last_log_size": activity_tracker["last_log_size"],
        "last_activity_time": activity_tracker["last_activity_time"],
        "idle_seconds": activity_tracker["idle_seconds"],
    }


def finalize_session_diagnostics(
    session,
    log_path,
    health_error,
    activity_tracker,
    last_payload=None,
    collect_diagnostics_fn=None,
):
    session.diagnostics = collect_diagnostics_fn(
        session.base_url,
        log_path,
        health_error,
        build_activity_state(activity_tracker),
        health_payload=last_payload,
    )


def build_health_snapshot(payload, error):
    if payload is not None:
        snapshot = {
            "ok": payload.get("ok"),
            "status": payload.get("status"),
        }
        if "port" in payload:
            snapshot["port"] = payload.get("port")
        return snapshot
    return {"ok": False, "status": "transport_error", "error": error}


def wait_for_session(
    session,
    timeout_seconds,
    activity_timeout_seconds=DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    health_timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    log_path=None,
    completion_predicate=None,
    timeout_message=None,
    iteration_observer=None,
    default_editor_log_path_fn=None,
    probe_health_fn=None,
    create_activity_tracker_fn=None,
    update_activity_tracker_fn=None,
    finalize_session_diagnostics_fn=None,
    time_ref=None,
):
    time_ref = time_module if time_ref is None else time_ref
    log_path = Path(log_path or session.effective_log_path or default_editor_log_path_fn())
    deadline = time_ref.time() + timeout_seconds
    last_health_error = None
    last_payload = None
    activity_tracker = create_activity_tracker_fn(log_path)
    completion_predicate = completion_predicate or (lambda payload: payload.get("ok") and payload.get("status") == "ready")

    while time_ref.time() < deadline:
        payload, error = probe_health_fn(session.base_url, health_timeout_seconds)
        if iteration_observer is not None:
            iteration_observer(payload, error)
        if payload is not None:
            last_payload = payload
            if completion_predicate(payload):
                update_activity_tracker_fn(activity_tracker, log_path)
                finalize_session_diagnostics_fn(session, log_path, None, activity_tracker, last_payload=payload)
                return session
            last_health_error = json.dumps(payload, ensure_ascii=True)
        else:
            last_health_error = error

        update_activity_tracker_fn(activity_tracker, log_path)

        if session.launched and session.process is not None and session.process.poll() is not None:
            finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["unity_exit_code"] = session.process.returncode
            raise UnityLaunchError(
                "Unity exited before ready with code {}".format(session.process.returncode),
                session=session,
            )

        if activity_timeout_seconds is not None and activity_tracker["idle_seconds"] >= activity_timeout_seconds:
            finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            raise UnityStalledError(
                "Unity log activity stalled for {:.1f} seconds".format(activity_tracker["idle_seconds"]),
                session=session,
            )

        time_ref.sleep(POLL_INTERVAL_SECONDS)

    update_activity_tracker_fn(activity_tracker, log_path)
    finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
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
    wait_for_session_fn=None,
):
    return wait_for_session_fn(
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
    wait_for_session_fn=None,
):
    observed_health = []
    recovery_seen = {"value": False}

    def observe(payload, error):
        snapshot = build_health_snapshot(payload, error)
        if not observed_health or observed_health[-1] != snapshot:
            observed_health.append(snapshot)
        status = snapshot.get("status")
        if status in recoverable_statuses or status == "transport_error":
            recovery_seen["value"] = True

    result = wait_for_session_fn(
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
    default_editor_log_path_fn=None,
    probe_health_fn=None,
    create_activity_tracker_fn=None,
    update_activity_tracker_fn=None,
    finalize_session_diagnostics_fn=None,
    read_editor_log_size_fn=None,
    read_editor_log_chunk_fn=None,
    time_ref=None,
):
    time_ref = time_module if time_ref is None else time_ref
    compiled_pattern = re.compile(pattern)
    log_path = Path(log_path or session.effective_log_path or default_editor_log_path_fn())
    deadline = time_ref.time() + timeout_seconds
    last_health_error = None
    last_payload = None
    activity_tracker = create_activity_tracker_fn(log_path)
    scan_offset = start_offset if start_offset is not None else read_editor_log_size_fn(log_path)

    while time_ref.time() < deadline:
        payload, error = probe_health_fn(session.base_url, health_timeout_seconds)
        if payload is not None:
            last_payload = payload
            last_health_error = json.dumps(payload, ensure_ascii=True)
            if expected_session_marker is not None:
                observed_session_marker = payload.get("session_marker")
                if not isinstance(observed_session_marker, str) or not observed_session_marker:
                    finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
                    raise UnitySessionStateError(
                        "session_missing",
                        "observation target did not provide session continuity information",
                        session=session,
                    )
                if observed_session_marker != expected_session_marker:
                    finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
                    raise UnitySessionStateError(
                        "session_stale",
                        "observation target session has changed since the expected session marker was recorded",
                        session=session,
                    )
        else:
            last_health_error = error

        chunk_start_offset = scan_offset
        scan_offset, chunk = read_editor_log_chunk_fn(log_path, scan_offset)
        update_activity_tracker_fn(activity_tracker, log_path)
        match = compiled_pattern.search(chunk)
        if match is not None:
            finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["matched_log_pattern"] = pattern
            session.diagnostics["matched_log_text"] = match.group(0)
            session.diagnostics["matched_log_offset"] = chunk_start_offset + len(chunk[: match.end()].encode("utf-8"))
            if extract_group is not None:
                session.diagnostics["extracted_group"] = match.group(extract_group)
            if extract_json_group is not None:
                session.diagnostics["extracted_json"] = json.loads(match.group(extract_json_group))
            return session

        if session.launched and session.process is not None and session.process.poll() is not None:
            finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            session.diagnostics["unity_exit_code"] = session.process.returncode
            raise UnityLaunchError(
                "Unity exited before log pattern matched with code {}".format(session.process.returncode),
                session=session,
            )

        if activity_timeout_seconds is not None and activity_tracker["idle_seconds"] >= activity_timeout_seconds:
            finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
            raise UnityStalledError(
                "Unity log activity stalled for {:.1f} seconds while waiting for log pattern".format(
                    activity_tracker["idle_seconds"]
                ),
                session=session,
            )

        time_ref.sleep(POLL_INTERVAL_SECONDS)

    update_activity_tracker_fn(activity_tracker, log_path)
    finalize_session_diagnostics_fn(session, log_path, last_health_error, activity_tracker, last_payload=last_payload)
    session.diagnostics["expected_log_pattern"] = pattern
    raise UnityNotReadyError(
        "Unity did not emit log pattern within {} seconds".format(timeout_seconds),
        session=session,
    )
