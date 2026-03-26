#!/usr/bin/env python3
import json
import time
from pathlib import Path

from unity_session_common import (
    LAUNCH_CLAIM_RELATIVE_PATH,
    PENDING_EXEC_DIR_RELATIVE_PATH,
    PENDING_EXEC_RETENTION_MS,
    PENDING_EXEC_SCHEMA_VERSION,
    PROJECT_RECOVERY_WINDOW_SECONDS,
    SESSION_RELATIVE_PATH,
    UNITY_LOCKFILE_RELATIVE_PATH,
)


def default_editor_log_path():
    local_app_data = Path.home() / "AppData" / "Local"
    return local_app_data / "Unity" / "Editor" / "Editor.log"


def read_recent_editor_log_lines(log_path, max_lines):
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


def read_editor_log_size(log_path):
    path = Path(log_path)
    if not path.exists():
        return None
    try:
        return path.stat().st_size
    except OSError:
        return None


def read_editor_log_chunk(log_path, start_offset):
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


def session_artifact_path(project_path):
    return Path(project_path) / SESSION_RELATIVE_PATH


def launch_claim_path(project_path):
    return Path(project_path) / LAUNCH_CLAIM_RELATIVE_PATH


def unity_lockfile_path(project_path):
    return Path(project_path) / UNITY_LOCKFILE_RELATIVE_PATH


def pending_exec_artifact_path(project_path, request_id):
    return Path(project_path) / PENDING_EXEC_DIR_RELATIVE_PATH / ("{}.json".format(request_id))


def pending_exec_dir_path(project_path):
    return Path(project_path) / PENDING_EXEC_DIR_RELATIVE_PATH


def _read_json_file(path):
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _write_json_file(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def _now_ms(time_ref=None):
    if time_ref is None:
        time_ref = time
    return int(time_ref.time() * 1000)


def _coerce_pending_exec_artifact(request_id, payload):
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != PENDING_EXEC_SCHEMA_VERSION:
        return None
    if payload.get("request_id") != request_id:
        return None
    code = payload.get("code")
    if not isinstance(code, str) or not code:
        return None
    created_at_ms = payload.get("created_at_ms")
    updated_at_ms = payload.get("updated_at_ms")
    if not isinstance(created_at_ms, int) or created_at_ms < 0:
        return None
    if not isinstance(updated_at_ms, int) or updated_at_ms < created_at_ms:
        return None

    normalized = {
        "schema_version": PENDING_EXEC_SCHEMA_VERSION,
        "request_id": request_id,
        "code": code,
        "refresh_before_exec": bool(payload.get("refresh_before_exec")),
        "reset_jsenv_before_exec": bool(payload.get("reset_jsenv_before_exec")),
        "created_at_ms": created_at_ms,
        "updated_at_ms": updated_at_ms,
    }
    script_args = payload.get("script_args")
    if not isinstance(script_args, dict):
        script_args = {}
    script_args_json = payload.get("script_args_json")
    if not isinstance(script_args_json, str) or not script_args_json:
        script_args_json = "{}"
    normalized["script_args"] = script_args
    normalized["script_args_json"] = script_args_json
    source_path = payload.get("source_path")
    if isinstance(source_path, str) and source_path:
        normalized["source_path"] = source_path
    import_base_url = payload.get("import_base_url")
    if isinstance(import_base_url, str) and import_base_url:
        normalized["import_base_url"] = import_base_url
    phase = payload.get("phase")
    if isinstance(phase, str) and phase:
        normalized["phase"] = phase
    refresh_request_id = payload.get("refresh_request_id")
    if isinstance(refresh_request_id, str) and refresh_request_id:
        normalized["refresh_request_id"] = refresh_request_id
    return normalized


def _is_pending_exec_artifact_expired(payload, now_ms):
    updated_at_ms = payload.get("updated_at_ms")
    if not isinstance(updated_at_ms, int):
        return True
    return updated_at_ms + PENDING_EXEC_RETENTION_MS < now_ms


def _delete_file_if_present(path):
    try:
        path.unlink()
    except FileNotFoundError:
        return


def sweep_pending_exec_artifacts(project_path, time_ref=None):
    now_ms = _now_ms(time_ref=time_ref)
    pending_dir = pending_exec_dir_path(project_path)
    if not pending_dir.exists():
        return []

    removed = []
    try:
        entries = list(pending_dir.glob("*.json"))
    except OSError:
        return removed

    for path in entries:
        request_id = path.stem
        payload = _read_json_file(path)
        normalized = _coerce_pending_exec_artifact(request_id, payload)
        if normalized is not None and not _is_pending_exec_artifact_expired(normalized, now_ms):
            continue
        _delete_file_if_present(path)
        removed.append(str(path))
    return removed


def read_session_artifact(project_path):
    return _read_json_file(session_artifact_path(project_path))


def write_session_artifact(project_path, payload):
    _write_json_file(session_artifact_path(project_path), payload)


def read_launch_claim(project_path):
    return _read_json_file(launch_claim_path(project_path))


def write_launch_claim(project_path, payload):
    _write_json_file(launch_claim_path(project_path), payload)


def clear_launch_claim(project_path):
    try:
        launch_claim_path(project_path).unlink()
    except FileNotFoundError:
        return


def read_pending_exec_artifact(project_path, request_id):
    path = pending_exec_artifact_path(project_path, request_id)
    payload = _read_json_file(path)
    normalized = _coerce_pending_exec_artifact(request_id, payload)
    if normalized is None:
        _delete_file_if_present(path)
        return None
    if _is_pending_exec_artifact_expired(normalized, _now_ms()):
        _delete_file_if_present(path)
        return None
    return normalized


def write_pending_exec_artifact(project_path, request_id, payload):
    path = pending_exec_artifact_path(project_path, request_id)
    existing = _coerce_pending_exec_artifact(request_id, _read_json_file(path))
    now_ms = _now_ms()
    script_args = payload.get("script_args")
    if not isinstance(script_args, dict):
        script_args = {}
    script_args_json = payload.get("script_args_json")
    if not isinstance(script_args_json, str) or not script_args_json:
        script_args_json = "{}"

    normalized = {
        "schema_version": PENDING_EXEC_SCHEMA_VERSION,
        "request_id": request_id,
        "code": payload["code"],
        "refresh_before_exec": bool(payload.get("refresh_before_exec")),
        "reset_jsenv_before_exec": bool(payload.get("reset_jsenv_before_exec")),
        "created_at_ms": existing.get("created_at_ms", now_ms) if existing else now_ms,
        "updated_at_ms": now_ms,
        "script_args": script_args,
        "script_args_json": script_args_json,
    }
    source_path = payload.get("source_path")
    if isinstance(source_path, str) and source_path:
        normalized["source_path"] = source_path
    import_base_url = payload.get("import_base_url")
    if isinstance(import_base_url, str) and import_base_url:
        normalized["import_base_url"] = import_base_url
    phase = payload.get("phase")
    if isinstance(phase, str) and phase:
        normalized["phase"] = phase
    refresh_request_id = payload.get("refresh_request_id")
    if isinstance(refresh_request_id, str) and refresh_request_id:
        normalized["refresh_request_id"] = refresh_request_id
    _write_json_file(path, normalized)
    return normalized


def clear_pending_exec_artifact(project_path, request_id):
    _delete_file_if_present(pending_exec_artifact_path(project_path, request_id))


def build_project_lock_details(project_path, time_ref):
    path = unity_lockfile_path(project_path)
    details = {
        "path": str(path),
        "exists": path.exists(),
        "fresh": False,
    }
    if not details["exists"]:
        return details
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return details
    age_seconds = round(max(0.0, time_ref.time() - mtime), 3)
    details["age_seconds"] = age_seconds
    details["fresh"] = age_seconds <= PROJECT_RECOVERY_WINDOW_SECONDS
    return details


def session_artifact_log_path(session_data, is_pid_running_fn):
    if not isinstance(session_data, dict):
        return None
    session_marker = session_data.get("session_marker")
    effective_log_path = session_data.get("effective_log_path")
    unity_pid = session_data.get("unity_pid")
    if not isinstance(session_marker, str) or not session_marker:
        return None
    if not isinstance(effective_log_path, str) or not effective_log_path:
        return None
    if unity_pid is not None and not is_pid_running_fn(unity_pid):
        return None
    return Path(effective_log_path)


def resolve_effective_log_path(
    project_path,
    unity_log_path=None,
    session_data=None,
    read_session_artifact_fn=None,
    session_artifact_log_path_fn=None,
    default_editor_log_path_fn=None,
):
    if session_data is None:
        session_data = read_session_artifact_fn(project_path)
    artifact_log_path = session_artifact_log_path_fn(session_data)
    if artifact_log_path is not None:
        return artifact_log_path
    if unity_log_path:
        return Path(unity_log_path)
    return default_editor_log_path_fn()


def session_marker_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    session_marker = payload.get("session_marker")
    if isinstance(session_marker, str) and session_marker:
        return session_marker
    return None


def persist_ready_session_artifact(
    session,
    effective_log_path,
    payload=None,
    session_marker_from_payload_fn=None,
    write_session_artifact_fn=None,
):
    session_marker = session_marker_from_payload_fn(payload)
    if session_marker is None and session.diagnostics:
        session_marker = session_marker_from_payload_fn(session.diagnostics.get("last_health_payload"))
    if not session_marker:
        return
    write_session_artifact_fn(
        session.project_path,
        {
            "base_url": session.base_url,
            "unity_pid": session.unity_pid,
            "session_marker": session_marker,
            "effective_log_path": str(effective_log_path),
        },
    )
