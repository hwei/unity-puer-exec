"""Shared retry and classification helpers for real-host harness cold launches.

Tolerates bounded transient cold-launch failures (e.g. unity_start_failed,
or Unity exiting before ready due to shutdown races) while never retrying
non-launch failures, compile errors, or genuine assertion failures.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple


TRANSIENT_LAUNCH_STATUS = "unity_start_failed"
EXITED_BEFORE_READY_MARKER = "Unity exited before ready"
DEFAULT_MAX_ATTEMPTS = 3


def is_transient_cold_launch_failure(
    exit_code: int,
    payload: Optional[Dict[str, Any]] = None,
    stdout: str = "",
    stderr: str = "",
) -> bool:
    """Classify whether a cold-launch failure is transient and eligible for retry.

    Returns True ONLY if:
    - exit_code != 0
    - And the failure is a launch failure where the CLI could not bring the
      Editor up: status == 'unity_start_failed' or error text indicates the
      launched Editor exited before ready.

    Returns False for:
    - exit_code == 0 (success)
    - Non-launch failures (syntax_error, compile_error, modal_blocked, busy, failed, etc.)
    - Non-launch process or CLI usage errors
    """
    if exit_code == 0:
        return False

    status = ""
    error = ""
    if isinstance(payload, dict):
        status = str(payload.get("status") or "").strip()
        error = str(payload.get("error") or "").strip()

    combined_text = " ".join(filter(None, [error, stdout or "", stderr or ""]))

    if status == TRANSIENT_LAUNCH_STATUS:
        return True

    if EXITED_BEFORE_READY_MARKER in combined_text:
        return True

    if f'"{TRANSIENT_LAUNCH_STATUS}"' in combined_text or f"'{TRANSIENT_LAUNCH_STATUS}'" in combined_text:
        return True

    return False


def record_retry_metadata(
    payload: Optional[Dict[str, Any]],
    attempt_count: int,
    last_launch_status: str,
    boundary_result: Optional[Any],
    attempts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Attach attempt and boundary diagnostic metadata to a payload dictionary.

    If payload is None, a new dictionary is synthesized.
    """
    if not isinstance(payload, dict):
        payload = {
            "ok": False,
            "status": last_launch_status or "unity_start_failed",
        }

    payload["attempt_count"] = attempt_count
    payload["last_launch_status"] = last_launch_status
    payload["boundary_result"] = boundary_result
    payload["attempts"] = attempts
    return payload


def warm_up_with_retry(
    warm_up_fn: Callable[..., Tuple[int, Optional[Dict[str, Any]], str, str]],
    project_path: Any,
    unity_exe_path: Any,
    ensure_clean_boundary_fn: Callable[[Any], Any],
    include_diagnostics: bool = False,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    is_editor_ready_fn: Optional[Callable[[Any], bool]] = None,
    transient_failure_injector: Optional[Callable[[int], Optional[Tuple[int, Dict[str, Any], str, str]]]] = None,
) -> Tuple[int, Optional[Dict[str, Any]], str, str]:
    """Run a project-scoped warm-up launch with bounded retry for transient launch failures.

    1. Checks if the Editor is already ready via is_editor_ready_fn; if not,
       confirms the clean boundary before attempting the launch.
    2. Runs warm_up_fn (or uses transient_failure_injector if configured for testing).
    3. If launch succeeds (exit_code == 0), attaches retry metadata and returns.
    4. If failure is NOT transient (e.g. compile error, syntax error, execution failure),
       stops immediately and returns without retrying.
    5. If failure IS transient, re-confirms the clean boundary and retries up to
       max_attempts.
    6. If max_attempts is exhausted, returns the last launch failure with attempt_count,
       last_launch_status, and boundary results recorded, making a persistent regression
       distinguishable from a transient flake.
    """
    if max_attempts < 1:
        max_attempts = 1

    attempts_history: List[Dict[str, Any]] = []
    last_boundary_result: Optional[Any] = None

    last_exit_code = 1
    last_payload: Optional[Dict[str, Any]] = None
    last_stdout = ""
    last_stderr = ""
    last_status = "unknown"

    for attempt in range(1, max_attempts + 1):
        # Before each launch attempt (cold launch attempt 1 or retry attempt > 1),
        # confirm the clean boundary unless the Editor is already ready.
        is_ready = False
        if is_editor_ready_fn is not None:
            try:
                is_ready = bool(is_editor_ready_fn(project_path))
            except Exception:
                is_ready = False

        if not is_ready:
            last_boundary_result = ensure_clean_boundary_fn(project_path)

        # Allow test injection of transient failure on specific attempt
        injected = None
        if transient_failure_injector is not None:
            injected = transient_failure_injector(attempt)

        if injected is not None:
            exit_code, payload, stdout, stderr = injected
        else:
            exit_code, payload, stdout, stderr = warm_up_fn(
                project_path,
                unity_exe_path,
                include_diagnostics=include_diagnostics,
            )

        status = (
            payload.get("status")
            if isinstance(payload, dict) and payload.get("status")
            else ("completed" if exit_code == 0 else "unknown")
        )

        last_exit_code = exit_code
        last_payload = payload
        last_stdout = stdout
        last_stderr = stderr
        last_status = str(status)

        attempt_record: Dict[str, Any] = {
            "attempt": attempt,
            "exit_code": exit_code,
            "status": last_status,
            "boundary_result": last_boundary_result,
        }
        if isinstance(payload, dict) and "error" in payload:
            attempt_record["error"] = payload["error"]

        attempts_history.append(attempt_record)

        if exit_code == 0:
            last_payload = record_retry_metadata(
                last_payload,
                attempt_count=attempt,
                last_launch_status=last_status,
                boundary_result=last_boundary_result,
                attempts=attempts_history,
            )
            return exit_code, last_payload, stdout, stderr

        if not is_transient_cold_launch_failure(exit_code, payload, stdout, stderr):
            # Non-transient failure: do not retry!
            last_payload = record_retry_metadata(
                last_payload,
                attempt_count=attempt,
                last_launch_status=last_status,
                boundary_result=last_boundary_result,
                attempts=attempts_history,
            )
            return exit_code, last_payload, stdout, stderr

        # Transient launch failure encountered. Continue loop if budget allows.

    # Exhausted all attempts: persistent launch regression
    last_payload = record_retry_metadata(
        last_payload,
        attempt_count=len(attempts_history),
        last_launch_status=last_status,
        boundary_result=last_boundary_result,
        attempts=attempts_history,
    )
    return last_exit_code, last_payload, last_stdout, last_stderr
