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
    UNITY_LOCKFILE_RELATIVE_PATH,
)


# Resolution tiers for the effective Unity log path, most to least authoritative.
# Reported by get-log-source so a caller can tell a path the Editor named from one
# the CLI assumed.
#
# The CLI-authored session artifact used to sit at the top of this list, on the
# reasoning that it was the tier that survived a health-probe failure. That
# reasoning is now served by the Editor's own publication, which is equally durable
# and, unlike the artifact, cannot name a log the target Editor is not writing to.
LOG_SOURCE_TIER_EXPLICIT_FLAG = "explicit_flag"
LOG_SOURCE_TIER_PUBLISHED_ENDPOINT = "published_endpoint"
LOG_SOURCE_TIER_CONTROL_SERVICE = "control_service"
LOG_SOURCE_TIER_PLATFORM_DEFAULT = "platform_default"

# Project-private Unity log for CLI-launched Editors. Under Temp/ because it is an
# observation surface for a live session, not an archive; a caller who needs a
# durable log passes --unity-log-path.
LAUNCH_LOG_RELATIVE_PATH = ("Temp", "UnityPuerExec", "Editor.log")


def default_editor_log_path():
    local_app_data = Path.home() / "AppData" / "Local"
    return local_app_data / "Unity" / "Editor" / "Editor.log"


def project_launch_log_path(project_path):
    return Path(project_path).joinpath(*LAUNCH_LOG_RELATIVE_PATH)


def prepare_launch_log_path(project_path, unity_log_path=None):
    """Pick the -logFile path for a CLI-launched Editor and make it writable.

    Without this the Editor binds to the per-user Editor.log, which an unrelated
    Editor on another project shares -- and byte-offset observation of a shared
    file reads the wrong content. Unity creates the log file itself but not its
    parent directory, so the directory is created here. A directory that cannot
    be created is not worth failing a launch over: the Editor still starts and
    resolution falls back through the remaining tiers.
    """
    path = Path(unity_log_path) if unity_log_path else project_launch_log_path(project_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


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
        "stale_module_policy": payload.get("stale_module_policy") if payload.get("stale_module_policy") in ("auto-reset", "error") else "auto-reset",
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
        "stale_module_policy": payload.get("stale_module_policy") if payload.get("stale_module_policy") in ("auto-reset", "error") else "auto-reset",
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


def publication_console_log_path(publication):
    if not isinstance(publication, dict):
        return None
    value = publication.get("console_log_path")
    if isinstance(value, str) and value:
        return Path(value)
    return None


def resolve_effective_log_path_with_tier(
    project_path,
    unity_log_path=None,
    publication=None,
    health_console_log_path=None,
    read_endpoint_publication_fn=None,
    default_editor_log_path_fn=None,
):
    """Resolve the observed log path and name the tier that produced it.

    Explicit caller intent wins, then the path the project's own Editor published,
    then whatever a live service says, and only then the platform default.

    The published path outranks the live service answer for the reason the removed
    session artifact used to: it keeps observation working when a health probe does
    not answer, so a momentary control-service failure cannot silently degrade
    observation to a per-user log that a second Editor may be sharing. Unlike the
    artifact, it costs nothing in correctness -- the Editor wrote it about itself.
    """
    if unity_log_path:
        return Path(unity_log_path), LOG_SOURCE_TIER_EXPLICIT_FLAG
    if publication is None and read_endpoint_publication_fn is not None:
        publication = read_endpoint_publication_fn(project_path)
    published_log_path = publication_console_log_path(publication)
    if published_log_path is not None:
        return published_log_path, LOG_SOURCE_TIER_PUBLISHED_ENDPOINT
    if health_console_log_path:
        return Path(health_console_log_path), LOG_SOURCE_TIER_CONTROL_SERVICE
    return default_editor_log_path_fn(), LOG_SOURCE_TIER_PLATFORM_DEFAULT


def resolve_effective_log_path(
    project_path,
    unity_log_path=None,
    publication=None,
    health_console_log_path=None,
    read_endpoint_publication_fn=None,
    default_editor_log_path_fn=None,
):
    path, _tier = resolve_effective_log_path_with_tier(
        project_path,
        unity_log_path=unity_log_path,
        publication=publication,
        health_console_log_path=health_console_log_path,
        read_endpoint_publication_fn=read_endpoint_publication_fn,
        default_editor_log_path_fn=default_editor_log_path_fn,
    )
    return path


def health_console_log_path(payload):
    if not isinstance(payload, dict):
        return None
    value = payload.get("console_log_path")
    if isinstance(value, str) and value:
        return value
    return None


def session_marker_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    session_marker = payload.get("session_marker")
    if isinstance(session_marker, str) and session_marker:
        return session_marker
    return None


# Nothing persists a session record here any more. The CLI does not write claims
# about a process it does not own; the Editor publishes its own endpoint, and the
# CLI reads it. See design D1 of let-editor-publish-session-endpoint -- if this
# looks like a convenience worth restoring, it is the defect, not the convenience.
