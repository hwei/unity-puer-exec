#!/usr/bin/env python3
import json
from pathlib import Path

from unity_session_common import SESSION_RELATIVE_PATH


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


def read_session_artifact(project_path):
    session_path = session_artifact_path(project_path)
    if not session_path.exists():
        return None
    with session_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_session_artifact(project_path, payload):
    session_path = session_artifact_path(project_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with session_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


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
