#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid

import cli_version
import direct_exec_client
import help_surface
import unity_log_brief
import unity_modal_blockers
import unity_session
import unity_session_logs


EXIT_RUNNING = direct_exec_client.EXIT_RUNNING
EXIT_COMPILING = direct_exec_client.EXIT_COMPILING
EXIT_NOT_AVAILABLE = direct_exec_client.EXIT_NOT_AVAILABLE
EXIT_MISSING = direct_exec_client.EXIT_MISSING
EXIT_BUSY = direct_exec_client.EXIT_BUSY
EXIT_REQUEST_ID_CONFLICT = direct_exec_client.EXIT_REQUEST_ID_CONFLICT
EXIT_MODAL_BLOCKED = direct_exec_client.EXIT_MODAL_BLOCKED
EXIT_MODULE_CACHE_STALE = direct_exec_client.EXIT_MODULE_CACHE_STALE
EXIT_UNITY_COMPILE_ERROR = direct_exec_client.EXIT_UNITY_COMPILE_ERROR
EXIT_VERSION_MISMATCH = direct_exec_client.EXIT_VERSION_MISMATCH
EXIT_SESSION_STATE = 14
EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
# A running Editor that never activated a control service. Distinct from a launch
# failure (20) and a readiness failure (21) so a caller can tell that retrying
# cannot help and an activation decision is what is missing.
EXIT_EDITOR_NOT_UNDER_CLI_CONTROL = 17
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21
STALE_MODULE_POLICY_AUTO_RESET = "auto-reset"
STALE_MODULE_POLICY_ERROR = "error"
RESULT_MARKER_PREFIX = "[UnityPuerExecResult]"
RESULT_MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"
PHASE_REFRESHING = "refreshing"
PHASE_COMPILING = "compiling"
PHASE_EXECUTING = "executing"
HEALTH_STATUS_READY = "ready"
HEALTH_STATUS_COMPILING = "compiling"
# Edge-aware wait-for-compile outcomes (see openspec compile-wait spec).
COMPILE_OUTCOME_READY = "ready"
COMPILE_OUTCOME_NONE = "no_compile_observed"
COMPILE_OUTCOME_TIMEOUT = "settle_timeout"
REFRESH_BEFORE_EXEC_TEMPLATE = """export default function run(ctx) {
  const AssetDatabase = puer.loadType('UnityEditor.AssetDatabase');
  AssetDatabase.Refresh();
  return { request_id: ctx.request_id, refreshed: true };
}
"""


def emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


def usage_error(message, status="failed", command=None, args=None):
    payload = {"ok": False, "status": status, "error": message}
    if command is not None and args is not None:
        _attach_guidance(payload, command, status, args)
    if status == "address_conflict":
        return 2, emit_payload(payload), ""
    return 2, "", emit_payload(payload)


_RESPONSE_FILE_ROUTING_FIELDS = (
    "ok",
    "status",
    "operation",
    "request_id",
    "phase",
    "session_marker",
    "cli_version",
)


def _inject_cli_version(text):
    """Stamp the acting CLI build onto a machine-readable response.

    Applied once at the end of `run_cli`, so every response family carries it --
    including the normalized exec/wait bodies and usage errors that never pass
    through the payload builders -- and before the response-file projection, so
    the compact reference inherits it through the routing fields.
    """
    if not text:
        return text
    try:
        body = json.loads(text)
    except ValueError:
        return text
    if not isinstance(body, dict) or "cli_version" in body:
        return text
    body["cli_version"] = cli_version.version_text(cli_version.resolve_cli_version())
    return emit_payload(body)


def _atomic_write_bytes(path, data):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".unity-puer-exec-response-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _project_response_file(response_file_path, exit_code, stdout_text, stderr_text):
    """Persist the exact unprojected JSON response to `response_file_path` and emit a
    compact verifiable reference on the same stream in its place (see design.md #2/#3).
    """
    if not response_file_path:
        return exit_code, stdout_text, stderr_text
    if stdout_text:
        stream, target_text = "stdout", stdout_text
    elif stderr_text:
        stream, target_text = "stderr", stderr_text
    else:
        return exit_code, stdout_text, stderr_text

    try:
        body = json.loads(target_text)
    except ValueError:
        return exit_code, stdout_text, stderr_text

    data = target_text.encode("utf-8")
    abs_path = os.path.abspath(response_file_path)

    try:
        _atomic_write_bytes(abs_path, data)
    except OSError as exc:
        if isinstance(body, dict):
            body["response_file_error"] = str(exc)
            new_text = emit_payload(body)
        else:
            new_text = target_text
        if stream == "stdout":
            return exit_code, new_text, stderr_text
        return exit_code, stdout_text, new_text

    reference = {}
    if isinstance(body, dict):
        for key in _RESPONSE_FILE_ROUTING_FIELDS:
            if key in body:
                reference[key] = body[key]
    reference["response_file"] = {
        "path": abs_path,
        "encoding": "utf-8",
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    ref_text = emit_payload(reference)
    if stream == "stdout":
        return exit_code, ref_text, stderr_text
    return exit_code, stdout_text, ref_text


def _canonicalize_script_args(raw_text):
    if raw_text is None:
        script_args = {}
    else:
        try:
            script_args = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid script-argument JSON: {}".format(exc.msg), "invalid_script_args_json") from exc
        if not isinstance(script_args, dict):
            raise ValueError("script arguments must be a JSON object", "invalid_script_args_type")
    script_args_json = json.dumps(script_args, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return script_args, script_args_json


def validate_positive(value, name):
    if value is not None and value <= 0:
        raise ValueError("{} must be positive".format(name))


def validate_non_negative(value, name):
    if value is not None and value < 0:
        raise ValueError("{} must be non-negative".format(name))


def validate_project_mode_only(selector, option_name, value):
    if selector == "base_url" and value:
        raise ValueError("{} is only valid with --project-path".format(option_name))


def _resolve_log_path(args, session):
    if session is not None and getattr(session, "effective_log_path", None):
        return session.effective_log_path
    if getattr(args, "unity_log_path", None):
        return args.unity_log_path
    return str(unity_session_logs.default_editor_log_path())


def _capture_log_offset(log_path):
    if log_path is None:
        return 0
    size = unity_session_logs.read_editor_log_size(log_path)
    return size if size is not None else 0


# brief_sequence sentinel + operator hint emitted when the Unity host reports that
# stack-trace logging is disabled. Without stack traces, runtime log briefs cannot
# reliably delimit entries (see openspec/specs/log-brief), so a real brief_sequence
# would be misleading. The C# server reports the condition via stack_trace_logging.degraded.
_BRIEF_SEQUENCE_STACKTRACE_OFF = "!stacktrace-off"
_BRIEF_HINT_STACKTRACE_OFF = (
    "Enable ScriptOnly/Full stack trace logging (Console > Stack Trace Logging or "
    "Application.SetStackTraceLogType) for meaningful log briefs."
)


def _stack_trace_logging_degraded(container):
    stack_trace_logging = container.get("stack_trace_logging")
    return isinstance(stack_trace_logging, dict) and bool(stack_trace_logging.get("degraded"))


def _detect_offset_invalidation(log_path, caller_start_offset):
    """Report a caller-supplied start offset that lies past the end of the log.

    Reading still rescans from the beginning -- dropping the read would be worse --
    but a byte range recorded before a rotation or truncation no longer denotes the
    content the caller meant, and absorbing that silently turns into an unexplained
    wait timeout. An observation that supplies no offset passes None here and cannot
    trip the signal.
    """
    if caller_start_offset is None or log_path is None:
        return None
    observed_end = unity_session_logs.read_editor_log_size(log_path)
    if observed_end is None or caller_start_offset <= observed_end:
        return None
    return {
        "log_path": str(log_path),
        "supplied_start": caller_start_offset,
        "observed_end": observed_end,
        "reason": "log_rotated_or_truncated",
        "detail": (
            "the supplied start offset {} is past the end ({}) of the observed log {}; "
            "the log was rotated or truncated, so earlier byte offsets no longer denote "
            "the intended content and the scan restarted from the beginning"
        ).format(caller_start_offset, observed_end, log_path),
    }


def _apply_log_range_and_brief_sequence(container, log_path, log_start, log_end, offsets_invalidated=None):
    container["log_range"] = {"start": log_start, "end": log_end}
    if offsets_invalidated is not None:
        container["log_offsets_invalidated"] = offsets_invalidated
    if _stack_trace_logging_degraded(container):
        container["brief_sequence"] = _BRIEF_SEQUENCE_STACKTRACE_OFF
        container["brief_hint"] = _BRIEF_HINT_STACKTRACE_OFF
        return
    briefs = unity_log_brief.parse_log_briefs(log_path, log_start, log_end)
    container["brief_sequence"] = unity_log_brief.build_brief_sequence(briefs)


def _inject_log_range_into_stdout(stdout_text, log_path, log_start, log_end, offsets_invalidated=None):
    if not stdout_text:
        return stdout_text
    body = json.loads(stdout_text)
    _apply_log_range_and_brief_sequence(body, log_path, log_start, log_end, offsets_invalidated=offsets_invalidated)
    return emit_payload(body)


def _inject_log_range_into_payload(payload, log_path, log_start, log_end, offsets_invalidated=None):
    _apply_log_range_and_brief_sequence(payload, log_path, log_start, log_end, offsets_invalidated=offsets_invalidated)


def resolve_selector(args):
    if getattr(args, "project_path", None) and getattr(args, "base_url", None):
        raise ValueError("address_conflict")
    if getattr(args, "base_url", None):
        return "base_url"
    return "project_path"


def success_payload(operation, session=None, result=None, include_diagnostics=False, diagnostics=None):
    payload = {"ok": True, "status": "completed", "operation": operation}
    if session is not None:
        payload["session"] = session.to_payload()
    if result is not None:
        payload["result"] = result
    return attach_diagnostics(payload, include_diagnostics=include_diagnostics, session=session, diagnostics=diagnostics)


def expected_failure_payload(operation, status, error, session=None, include_diagnostics=False, diagnostics=None):
    payload = {"ok": False, "status": status, "operation": operation, "error": str(error)}
    if session is not None:
        payload["session"] = session.to_payload()
    return attach_diagnostics(payload, include_diagnostics=include_diagnostics, session=session, diagnostics=diagnostics)


def unexpected_failure_payload(operation, error, session=None, include_diagnostics=False, diagnostics=None):
    payload = {"ok": False, "status": "failed", "operation": operation, "error": str(error)}
    if session is not None:
        payload["session"] = session.to_payload()
    return attach_diagnostics(payload, include_diagnostics=include_diagnostics, session=session, diagnostics=diagnostics)


def version_mismatch_payload(operation, detail):
    return {
        "ok": False,
        "status": cli_version.STATUS_VERSION_MISMATCH,
        "operation": operation,
        "error": cli_version.mismatch_message(detail),
        "version_mismatch": dict(detail),
    }


def _version_mismatch_result(args, detail):
    payload = version_mismatch_payload(args.command, detail)
    _attach_guidance(payload, args.command, cli_version.STATUS_VERSION_MISMATCH, args)
    return EXIT_VERSION_MISMATCH, emit_payload(payload), ""


def _local_version_guards(args):
    """Guards that need nothing but the local installation, run before any work."""
    argv0 = getattr(args, "argv0", None)
    resolved = cli_version.resolve_cli_version()
    detail = cli_version.check_cli_version_known(resolved, argv0=argv0)
    if detail is not None:
        return detail
    return cli_version.check_package_layout(resolved, argv0=argv0)


def _base_url_bridge_guard(args):
    """Bridge guard for the selector that never otherwise probes health.

    A transport failure is not a guard failure: the endpoint reported nothing to
    compare, and the command's own not_available handling is the right answer.
    """
    try:
        if resolve_selector(args) != "base_url":
            return None
    except ValueError:
        # A malformed selector combination is a usage error; let the command say so
        # rather than spending a probe on an invocation that cannot run.
        return None
    base_url = args.base_url
    payload, error = unity_session.probe_health_payload(base_url)
    if payload is None or error is not None:
        return None
    return cli_version.check_bridge(cli_version.resolve_cli_version(), base_url, payload)


def run_command(args):
    detail = _local_version_guards(args)
    if detail is None:
        detail = _base_url_bridge_guard(args)
    if detail is not None:
        return _version_mismatch_result(args, detail)
    try:
        if args.command == "exec":
            return run_exec(args)
        if args.command == "wait-for-exec":
            return run_wait_for_exec(args)
        if args.command == "wait-for-log-pattern":
            return run_wait_for_log_pattern(args)
        if args.command == "wait-for-result-marker":
            return run_wait_for_result_marker(args)
        if args.command == "wait-for-compile":
            return run_wait_for_compile(args)
        if args.command == "get-log-source":
            return run_get_log_source(args)
        if args.command == "get-blocker-state":
            return run_get_blocker_state(args)
        if args.command == "resolve-blocker":
            return run_resolve_blocker(args)
        if args.command == "get-log-briefs":
            return run_get_log_briefs(args)
        if args.command == "get-compile-errors":
            return run_get_compile_errors(args)
        if args.command == "get-compile-warnings":
            return run_get_compile_warnings(args)
        return run_ensure_stopped(args)
    except unity_session.UnityVersionMismatchError as exc:
        return _version_mismatch_result(args, exc.detail)
    except ValueError as exc:
        if len(exc.args) >= 2 and isinstance(exc.args[1], str):
            return usage_error(str(exc.args[0]), status=exc.args[1], command=args.command, args=args)
        status = "address_conflict" if str(exc) == "address_conflict" else "failed"
        return usage_error(str(exc), status=status, command=args.command, args=args)
    except unity_session.UnityLaunchError as exc:
        payload = expected_failure_payload(
            args.command,
            "unity_start_failed",
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        _attach_guidance(payload, args.command, "unity_start_failed", args, request_id=getattr(args, "request_id", None))
        return EXIT_UNITY_START_FAILED, emit_payload(payload), ""
    except unity_session.UnityLaunchConflictError as exc:
        payload = expected_failure_payload(
            args.command,
            "launch_conflict",
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        _attach_guidance(payload, args.command, "launch_conflict", args, request_id=getattr(args, "request_id", None))
        return EXIT_UNITY_START_FAILED, emit_payload(payload), ""
    except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
        status = "unity_stalled" if isinstance(exc, unity_session.UnityStalledError) else "unity_not_ready"
        payload = expected_failure_payload(
            args.command,
            status,
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        _attach_guidance(payload, args.command, status, args, request_id=getattr(args, "request_id", None))
        return EXIT_UNITY_NOT_READY, emit_payload(payload), ""
    except unity_session.UnityEditorNotUnderControlError as exc:
        # Its own exit code, distinct from launch (20) and readiness (21) failures,
        # because the remedy is an activation decision rather than a retry.
        payload = expected_failure_payload(
            args.command,
            exc.status,
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        payload["ways_forward"] = list(exc.guidance)
        _attach_guidance(payload, args.command, exc.status, args)
        return EXIT_EDITOR_NOT_UNDER_CLI_CONTROL, emit_payload(payload), ""
    except unity_session.UnitySessionStateError as exc:
        payload = expected_failure_payload(
            args.command,
            exc.status,
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        _attach_guidance(payload, args.command, exc.status, args)
        return EXIT_SESSION_STATE, emit_payload(payload), ""
    except Exception as exc:  # noqa: BLE001 - CLI should normalize unexpected failures.
        payload = unexpected_failure_payload(
            args.command,
            exc,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        _attach_guidance(payload, args.command, "failed", args)
        return 1, emit_payload(payload), ""


def run_cli(argv, surface, argv0=None):
    filtered_argv = [a for a in argv if a != "--suppress-guidance"]
    version_result = surface.handle_version(filtered_argv)
    if version_result is not None:
        return version_result
    help_result = surface.handle_top_level_help(filtered_argv)
    if help_result is not None:
        return help_result
    help_result = surface.handle_command_help(filtered_argv)
    if help_result is not None:
        return help_result
    parser = surface.build_parser()
    args = parser.parse_args(argv)
    args.argv0 = argv0
    exit_code, stdout_text, stderr_text = run_command(args)
    stdout_text = _inject_cli_version(stdout_text)
    stderr_text = _inject_cli_version(stderr_text)
    return _project_response_file(getattr(args, "response_file", None), exit_code, stdout_text, stderr_text)


def read_exec_code(args):
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    return args.code


def _project_path_arg(args):
    return str(unity_session.resolve_project_path(getattr(args, "project_path", None), argv0=getattr(args, "argv0", None)))


def _build_guidance_context(args, request_id=None):
    context = {}
    project_path = getattr(args, "project_path", None)
    if project_path:
        context["project_path"] = str(unity_session.resolve_project_path(project_path))
    if request_id:
        context["request_id"] = request_id
    if getattr(args, "wait_timeout_ms", None) is not None:
        context["wait_timeout_ms"] = args.wait_timeout_ms
    if getattr(args, "unity_exe_path", None):
        context["unity_exe_path"] = args.unity_exe_path
    if getattr(args, "unity_log_path", None):
        context["unity_log_path"] = args.unity_log_path
    if getattr(args, "file_path", None):
        context["file_path"] = str(args.file_path)
    if getattr(args, "include_diagnostics", False):
        context["include_diagnostics"] = True
    return context


_BARE_PUER_REFERENCE_ERROR_RE = re.compile(r"^ReferenceError: \$(typeof|ref) is not defined$")


def _maybe_hint_puer_prefix(payload, command):
    if command not in ("exec", "wait-for-exec") or payload.get("status") != "failed":
        return
    error = payload.get("error")
    if not isinstance(error, str):
        return
    match = _BARE_PUER_REFERENCE_ERROR_RE.match(error.strip())
    if match is None:
        return
    name = match.group(1)
    hint = "This looks like a missing `puer.` prefix: did you mean `puer.${}` instead of bare `${}`?".format(name, name)
    situation = payload.get("situation")
    payload["situation"] = "{} {}".format(situation, hint) if situation else hint


def _attach_guidance(payload, command, status, args, request_id=None):
    if getattr(args, "suppress_guidance", False):
        return
    context = _build_guidance_context(args, request_id=request_id)
    next_steps = help_surface.build_next_steps(command, status, context)
    if next_steps:
        payload["next_steps"] = next_steps
    detail = payload.get("version_mismatch")
    guard = detail.get("guard") if isinstance(detail, dict) else None
    situation = help_surface.build_situation(command, status, guard=guard)
    if situation:
        payload["situation"] = situation
    _maybe_hint_puer_prefix(payload, command)


def _inject_guidance_into_stdout(stdout_text, command, args, request_id=None):
    if not stdout_text or getattr(args, "suppress_guidance", False):
        return stdout_text
    body = json.loads(stdout_text)
    rid = request_id or body.get("request_id")
    _attach_guidance(body, command, body.get("status"), args, request_id=rid)
    return emit_payload(body)


def _inject_guidance_into_response(stdout_text, stderr_text, command, args, request_id=None):
    """Like _inject_guidance_into_stdout, but also covers the stderr-carried case.

    exec/wait-for-exec route some failed responses (e.g. a thrown script error) to
    stderr rather than stdout; guidance built from GUIDANCE_MATRIX -- including the
    puer. prefix hint -- must reach those responses too.
    """
    if stdout_text:
        return _inject_guidance_into_stdout(stdout_text, command, args, request_id=request_id), stderr_text
    if not stderr_text or getattr(args, "suppress_guidance", False):
        return stdout_text, stderr_text
    body = json.loads(stderr_text)
    rid = request_id or body.get("request_id")
    _attach_guidance(body, command, body.get("status"), args, request_id=rid)
    return stdout_text, emit_payload(body)


def _refresh_request_id(request_id):
    return "{}-refresh".format(request_id)


def _pending_exec_payload(
    request_id,
    code,
    script_args,
    script_args_json,
    refresh_before_exec=False,
    phase=None,
    refresh_request_id=None,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args": script_args,
        "script_args_json": script_args_json,
        "refresh_before_exec": bool(refresh_before_exec),
        "reset_jsenv_before_exec": bool(reset_jsenv_before_exec),
        "stale_module_policy": stale_module_policy or STALE_MODULE_POLICY_AUTO_RESET,
    }
    if source_path:
        payload["source_path"] = source_path
    if import_base_url:
        payload["import_base_url"] = import_base_url
    if phase:
        payload["phase"] = phase
    if refresh_request_id:
        payload["refresh_request_id"] = refresh_request_id
    return payload


def _sweep_pending_exec(args):
    project_path = _project_path_arg(args)
    if project_path:
        unity_session.sweep_pending_exec_artifacts(project_path)


def _write_pending_exec(
    args,
    request_id,
    code,
    script_args,
    script_args_json,
    refresh_before_exec=False,
    phase=None,
    refresh_request_id=None,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    _sweep_pending_exec(args)
    return unity_session.write_pending_exec_artifact(
        _project_path_arg(args),
        request_id,
        _pending_exec_payload(
            request_id,
            code,
            script_args,
            script_args_json,
            refresh_before_exec=refresh_before_exec,
            phase=phase,
            refresh_request_id=refresh_request_id,
            source_path=source_path,
            import_base_url=import_base_url,
            reset_jsenv_before_exec=reset_jsenv_before_exec,
            stale_module_policy=stale_module_policy,
        ),
    )


def _read_pending_exec(args, request_id):
    _sweep_pending_exec(args)
    return unity_session.read_pending_exec_artifact(_project_path_arg(args), request_id)


def _clear_pending_exec(args, request_id):
    unity_session.clear_pending_exec_artifact(_project_path_arg(args), request_id)


def _refresh_pending_exec(args, request_id, pending, phase=None):
    if pending is None:
        return None
    updated = dict(pending)
    if phase:
        updated["phase"] = phase
    return unity_session.write_pending_exec_artifact(_project_path_arg(args), request_id, updated)


def _finalize_pending_after_submit(args, request_id, pending, exit_code, stdout_text):
    if _is_compiling_response(exit_code, stdout_text):
        return _refresh_pending_exec(args, request_id, pending, PHASE_COMPILING)
    if _should_keep_pending_after_submit(exit_code, stdout_text):
        return _refresh_pending_exec(args, request_id, pending, _pending_phase(pending))
    _clear_pending_exec(args, request_id)
    return None


def _emit_running_payload(operation, session, request_id, args, phase=None):
    payload = {
        "ok": True,
        "status": "running",
        "operation": operation,
        "request_id": request_id,
    }
    if phase:
        payload["phase"] = phase
    if session is not None:
        payload["session"] = session.to_payload()
    _attach_guidance(payload, operation, "running", args, request_id=request_id)
    return attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)


def _build_exec_payload(
    request_id,
    code,
    script_args_json,
    args,
    source_path=None,
    import_base_url=None,
    refresh_before_exec=False,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args_json": script_args_json,
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_diagnostics": args.include_diagnostics,
        "stale_module_policy": stale_module_policy or STALE_MODULE_POLICY_AUTO_RESET,
    }
    if source_path:
        payload["source_path"] = source_path
    if import_base_url:
        payload["import_base_url"] = import_base_url
    if reset_jsenv_before_exec:
        payload["reset_jsenv_before_exec"] = True
    if refresh_before_exec:
        payload["refresh_before_exec"] = True
    return payload


def _invoke_exec(
    base_url,
    request_id,
    code,
    script_args_json,
    args,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    refresh_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = _build_exec_payload(
        request_id,
        code,
        script_args_json,
        args,
        source_path=source_path,
        import_base_url=import_base_url,
        reset_jsenv_before_exec=reset_jsenv_before_exec,
        refresh_before_exec=refresh_before_exec,
        stale_module_policy=stale_module_policy,
    )
    return direct_exec_client.invoke_command(
        "exec",
        base_url,
        payload,
        args.wait_timeout_ms,
    )


def _post_refresh_ready_timeout_seconds(args):
    return max(float(args.wait_timeout_ms) / 1000.0, 0.001)


def _ensure_project_session_ready_after_refresh(args):
    return unity_session.ensure_session_ready(
        project_path=args.project_path,
        unity_exe_path=args.unity_exe_path,
        unity_log_path=args.unity_log_path,
        unity_launch_args=getattr(args, "unity_launch_args", None),
        ready_timeout_seconds=_post_refresh_ready_timeout_seconds(args),
        argv0=getattr(args, "argv0", None),
    )


def _probe_compile_health(base_url, health_timeout_seconds):
    return unity_session._probe_health(base_url, health_timeout_seconds)


def _record_observed_status(observed, status):
    if status is not None and (not observed or observed[-1] != status):
        observed.append(status)


def wait_for_compile_cycle(
    base_url,
    appear_timeout_seconds,
    settle_timeout_seconds,
    health_timeout_seconds,
    appear_poll_interval=unity_session.COMPILE_APPEAR_POLL_INTERVAL_SECONDS,
    settle_poll_interval=unity_session.POLL_INTERVAL_SECONDS,
    probe_health_fn=None,
    time_ref=None,
):
    """Edge-aware wait for a single Unity compilation cycle over `/health`.

    Phase 1 (appear): within ``appear_timeout_seconds`` wait for the editor to
    report ``compiling`` (or detect a compile already in progress). An initial
    ``ready`` is never treated as terminal, defeating the async-refresh race. If a
    previously-ready endpoint drops (transport error after a healthy probe), that is
    treated as a domain-reload edge.

    Phase 2 (settle): wait up to ``settle_timeout_seconds`` for the editor to return
    to ``ready``. Transient transport errors during this phase are tolerated as
    still-in-progress until the ready/timeout boundary.

    Returns a dict with ``outcome`` in {``ready``, ``no_compile_observed``,
    ``settle_timeout``} and the ``observed_health`` status sequence.
    """
    time_ref = time if time_ref is None else time_ref
    probe_health_fn = probe_health_fn or _probe_compile_health
    observed = []
    seen_healthy = False
    edge_observed = False

    appear_deadline = time_ref.time() + appear_timeout_seconds
    while True:
        payload, _error = probe_health_fn(base_url, health_timeout_seconds)
        status = payload.get("status") if isinstance(payload, dict) else None
        _record_observed_status(observed, status)
        if status == HEALTH_STATUS_COMPILING:
            edge_observed = True
            break
        if status == HEALTH_STATUS_READY:
            seen_healthy = True
        elif payload is None and seen_healthy:
            # Endpoint dropped after being healthy: a refresh-triggered domain reload
            # tears the control endpoint down, so treat this as the compile edge.
            edge_observed = True
            break
        if time_ref.time() >= appear_deadline:
            break
        time_ref.sleep(appear_poll_interval)

    if not edge_observed:
        return {"outcome": COMPILE_OUTCOME_NONE, "observed_health": observed}

    settle_deadline = time_ref.time() + settle_timeout_seconds
    while True:
        payload, _error = probe_health_fn(base_url, health_timeout_seconds)
        status = payload.get("status") if isinstance(payload, dict) else None
        _record_observed_status(observed, status)
        if status == HEALTH_STATUS_READY:
            return {"outcome": COMPILE_OUTCOME_READY, "observed_health": observed}
        if time_ref.time() >= settle_deadline:
            return {"outcome": COMPILE_OUTCOME_TIMEOUT, "observed_health": observed}
        time_ref.sleep(settle_poll_interval)


def _settle_base_url_after_refresh(base_url, args):
    """Base-url analog of `_ensure_project_session_ready_after_refresh`.

    Re-probes the same caller-supplied endpoint, reusing the compile-wait primitive,
    so refresh-before-exec settles on the compile cycle before running the script.
    """
    settle_timeout_seconds = _post_refresh_ready_timeout_seconds(args)
    return wait_for_compile_cycle(
        base_url,
        getattr(args, "appear_timeout_seconds", unity_session.DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS),
        settle_timeout_seconds,
        getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS),
    )


def _refresh_exec_code():
    return REFRESH_BEFORE_EXEC_TEMPLATE


def _invoke_refresh_exec(base_url, request_id, args):
    return _invoke_exec(base_url, request_id, _refresh_exec_code(), "{}", args, refresh_before_exec=True)


def _invoke_reset_jsenv(base_url, args):
    return direct_exec_client.invoke_command(
        "reset-jsenv",
        base_url,
        {},
        args.wait_timeout_ms,
    )


def _running_or_timed_out_response(exit_code, stdout_text):
    if not stdout_text:
        return False
    body = json.loads(stdout_text)
    status = body.get("status")
    if status == "running":
        return True
    return exit_code == EXIT_NOT_AVAILABLE and status == "not_available" and body.get("error") == "timed out"


def _is_compiling_response(exit_code, stdout_text):
    if exit_code != EXIT_COMPILING or not stdout_text:
        return False
    body = json.loads(stdout_text)
    return body.get("status") == "compiling"


def _normalize_exec_lifecycle_body(body, args, request_id=None, default_phase=None, normalize_compiling=True):
    if not isinstance(body, dict):
        return body, None
    if not getattr(args, "project_path", None):
        return body, None
    status = body.get("status")
    if normalize_compiling and status == "compiling":
        normalized_request_id = request_id or body.get("request_id")
        body["ok"] = True
        body["status"] = "running"
        if normalized_request_id:
            body["request_id"] = normalized_request_id
        body["phase"] = PHASE_COMPILING
        return body, EXIT_RUNNING
    if status == "running":
        normalized_request_id = request_id or body.get("request_id")
        if normalized_request_id:
            body["request_id"] = normalized_request_id
        body.setdefault("phase", default_phase or PHASE_EXECUTING)
        return body, EXIT_RUNNING
    return body, None


def _remap_request_id_in_response(text, request_id, args, phase=None, normalize_compiling=True):
    if not text:
        return text
    body = json.loads(text)
    body["request_id"] = request_id
    body, _ = _normalize_exec_lifecycle_body(
        body,
        args,
        request_id=request_id,
        default_phase=phase,
        normalize_compiling=normalize_compiling,
    )
    return emit_payload(body)


def _pending_phase(pending):
    if not isinstance(pending, dict):
        return None
    phase = pending.get("phase")
    return phase if isinstance(phase, str) and phase else None


def _set_pending_phase(args, request_id, pending, phase):
    return _refresh_pending_exec(args, request_id, pending, phase)


def _normalize_exec_response(
    exit_code,
    stdout_text,
    stderr_text,
    args,
    request_id=None,
    default_phase=None,
    normalize_compiling=True,
):
    if stdout_text:
        body = json.loads(stdout_text)
        body, normalized_exit_code = _normalize_exec_lifecycle_body(
            body,
            args,
            request_id=request_id,
            default_phase=default_phase,
            normalize_compiling=normalize_compiling,
        )
        if normalized_exit_code is not None:
            exit_code = normalized_exit_code
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stdout_text = emit_payload(body)
    if stderr_text:
        body = json.loads(stderr_text)
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stderr_text = emit_payload(body)
    return exit_code, stdout_text, stderr_text


def _should_keep_pending_after_submit(exit_code, stdout_text):
    if not stdout_text:
        return False
    body = json.loads(stdout_text)
    status = body.get("status")
    if exit_code == EXIT_COMPILING and status == "compiling":
        return True
    return exit_code == EXIT_NOT_AVAILABLE and status == "not_available"


def _resolve_source_path(args):
    if getattr(args, "file_path", None):
        return os.path.abspath(args.file_path)
    return None


def _exec_import_base_url(args):
    value = getattr(args, "import_base_url", None)
    return value if value else None


def _exec_reset_flag(args):
    return bool(getattr(args, "reset_jsenv_before_exec", False))


def _exec_stale_module_policy(args):
    return getattr(args, "stale_module_policy", None) or STALE_MODULE_POLICY_AUTO_RESET


def run_exec(args):
    if getattr(args, "include_log_offset", False):
        return usage_error(
            "--include-log-offset has been removed; use log_range.start from exec response",
            command="exec",
            args=args,
        )
    request_id = args.request_id or uuid.uuid4().hex
    code = read_exec_code(args)
    script_args, script_args_json = _canonicalize_script_args(getattr(args, "script_args", None))
    source_path = _resolve_source_path(args)
    import_base_url = _exec_import_base_url(args)
    reset_jsenv_before_exec = _exec_reset_flag(args)
    stale_module_policy = _exec_stale_module_policy(args)
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))
    # refresh-before-exec is now allowed in base-url mode: the server accepts
    # refresh_before_exec for any selector, and the base-url settle path re-probes the
    # same endpoint (see _settle_base_url_after_refresh).

    if selector == "project_path":
        _sweep_pending_exec(args)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
                unity_launch_args=getattr(args, "unity_launch_args", None),
                argv0=getattr(args, "argv0", None),
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            _write_pending_exec(
                args,
                request_id,
                code,
                script_args,
                script_args_json,
                refresh_before_exec=args.refresh_before_exec,
                source_path=source_path,
                import_base_url=import_base_url,
                reset_jsenv_before_exec=reset_jsenv_before_exec,
                stale_module_policy=stale_module_policy,
            )
            payload = _emit_running_payload("exec", exc.session, request_id, args)
            _rp1_log_path = _resolve_log_path(args, exc.session)
            _rp1_log_end = _capture_log_offset(_rp1_log_path)
            _inject_log_range_into_payload(payload, _rp1_log_path, _rp1_log_end, _rp1_log_end)
            return EXIT_RUNNING, emit_payload(payload), ""
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    log_path = _resolve_log_path(args, session)
    log_start = _capture_log_offset(log_path)
    _bring_unity_to_foreground(session)

    if selector == "project_path" and args.refresh_before_exec:
        refresh_request_id = _refresh_request_id(request_id)
        _write_pending_exec(
            args,
            request_id,
            code,
            script_args,
            script_args_json,
            refresh_before_exec=True,
            phase=PHASE_REFRESHING,
            refresh_request_id=refresh_request_id,
            source_path=source_path,
            import_base_url=import_base_url,
            reset_jsenv_before_exec=reset_jsenv_before_exec,
            stale_module_policy=stale_module_policy,
        )
        exit_code, stdout_text, stderr_text = _invoke_refresh_exec(base_url, refresh_request_id, args)
        exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
            exit_code,
            stdout_text,
            stderr_text,
            session,
            log_path=log_path,
        )
        if _running_or_timed_out_response(exit_code, stdout_text):
            _refresh_pending_exec(args, request_id, _read_pending_exec(args, request_id), PHASE_REFRESHING)
            payload = _emit_running_payload("exec", session, request_id, args, phase=PHASE_REFRESHING)
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
            return EXIT_RUNNING, emit_payload(payload), ""
        if exit_code != 0:
            _clear_pending_exec(args, request_id)
            stdout_text = _remap_request_id_in_response(
                stdout_text,
                request_id,
                args,
                phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            stderr_text = _remap_request_id_in_response(
                stderr_text,
                request_id,
                args,
                phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            exit_code, stdout_text, stderr_text = _normalize_exec_response(
                exit_code,
                stdout_text,
                stderr_text,
                args,
                request_id=request_id,
                default_phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            stdout_text = _inject_log_range_into_stdout(stdout_text, log_path, log_start, _capture_log_offset(log_path))
            stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "exec", args, request_id=request_id)
            return exit_code, stdout_text, stderr_text
        try:
            session = _ensure_project_session_ready_after_refresh(args)
            base_url = session.base_url
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            _refresh_pending_exec(args, request_id, _read_pending_exec(args, request_id), PHASE_REFRESHING)
            payload = _emit_running_payload("exec", exc.session, request_id, args, phase=PHASE_REFRESHING)
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
            return EXIT_RUNNING, emit_payload(payload), ""
        _set_pending_phase(args, request_id, _read_pending_exec(args, request_id), PHASE_EXECUTING)

    if selector == "base_url" and args.refresh_before_exec:
        refresh_request_id = _refresh_request_id(request_id)
        refresh_exit_code, refresh_stdout_text, refresh_stderr_text = _invoke_refresh_exec(
            base_url, refresh_request_id, args
        )
        refresh_in_progress = _running_or_timed_out_response(
            refresh_exit_code, refresh_stdout_text
        ) or _is_compiling_response(refresh_exit_code, refresh_stdout_text)
        if refresh_exit_code != 0 and not refresh_in_progress:
            refresh_stdout_text = _remap_request_id_in_response(
                refresh_stdout_text,
                request_id,
                args,
                phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            refresh_stderr_text = _remap_request_id_in_response(
                refresh_stderr_text,
                request_id,
                args,
                phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            refresh_exit_code, refresh_stdout_text, refresh_stderr_text = _normalize_exec_response(
                refresh_exit_code,
                refresh_stdout_text,
                refresh_stderr_text,
                args,
                request_id=request_id,
                default_phase=PHASE_REFRESHING,
                normalize_compiling=False,
            )
            refresh_stdout_text = _inject_log_range_into_stdout(
                refresh_stdout_text, log_path, log_start, _capture_log_offset(log_path)
            )
            refresh_stdout_text, refresh_stderr_text = _inject_guidance_into_response(
                refresh_stdout_text, refresh_stderr_text, "exec", args, request_id=request_id
            )
            return refresh_exit_code, refresh_stdout_text, refresh_stderr_text
        # Settle on the compile cycle by re-probing the same endpoint, then run the
        # user script below so base-url callers get refresh -> compile-settle -> execute.
        _settle_base_url_after_refresh(base_url, args)

    exit_code, stdout_text, stderr_text = _invoke_exec(
        base_url,
        request_id,
        code,
        script_args_json,
        args,
        source_path=source_path,
        import_base_url=import_base_url,
        reset_jsenv_before_exec=reset_jsenv_before_exec,
        stale_module_policy=stale_module_policy,
    )
    exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
        exit_code,
        stdout_text,
        stderr_text,
        session if selector == "project_path" else None,
        log_path=log_path if selector == "project_path" else None,
    )
    if selector == "project_path":
        pending = _read_pending_exec(args, request_id)
        _finalize_pending_after_submit(args, request_id, pending, exit_code, stdout_text)
    default_phase = PHASE_COMPILING if _is_compiling_response(exit_code, stdout_text) else None
    exit_code, stdout_text, stderr_text = _normalize_exec_response(
        exit_code,
        stdout_text,
        stderr_text,
        args,
        request_id=request_id,
        default_phase=default_phase,
    )
    stdout_text = _inject_log_range_into_stdout(stdout_text, log_path, log_start, _capture_log_offset(log_path))
    stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "exec", args, request_id=request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_for_exec(args):
    if getattr(args, "include_log_offset", False):
        return usage_error(
            "--include-log-offset has been removed; use log_range.start from exec response",
            command="wait-for-exec",
            args=args,
        )
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    _wfe_log_path_early = getattr(args, "unity_log_path", None) or str(unity_session_logs.default_editor_log_path())
    _wfe_log_start = args.log_start_offset if args.log_start_offset is not None else _capture_log_offset(_wfe_log_path_early)
    _wfe_offsets_invalidated = _detect_offset_invalidation(_wfe_log_path_early, args.log_start_offset)

    if selector == "project_path":
        _sweep_pending_exec(args)
        pending = _read_pending_exec(args, args.request_id)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
                unity_launch_args=getattr(args, "unity_launch_args", None),
                argv0=getattr(args, "argv0", None),
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            if pending is not None:
                pending = _refresh_pending_exec(args, args.request_id, pending, _pending_phase(pending))
                payload = _emit_running_payload(
                    "wait-for-exec",
                    exc.session,
                    args.request_id,
                    args,
                    phase=_pending_phase(pending),
                )
                _wfe_rp1_log_path = _resolve_log_path(args, exc.session)
                _inject_log_range_into_payload(payload, _wfe_rp1_log_path, _wfe_log_start, _capture_log_offset(_wfe_rp1_log_path), offsets_invalidated=_wfe_offsets_invalidated)
                return EXIT_RUNNING, emit_payload(payload), ""
            raise
        base_url = session.base_url
        _bring_unity_to_foreground(session)
    else:
        session = None
        base_url = args.base_url
        pending = None
    if pending is not None:
        if pending.get("refresh_before_exec") and pending.get("phase") == PHASE_REFRESHING:
            refresh_request_id = pending.get("refresh_request_id") or _refresh_request_id(args.request_id)
            _wfe_refresh_log_path = _resolve_log_path(args, session)
            payload = {
                "request_id": refresh_request_id,
                "wait_timeout_ms": args.wait_timeout_ms,
                "include_diagnostics": args.include_diagnostics,
            }
            exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
                "wait-for-exec",
                base_url,
                payload,
                args.wait_timeout_ms,
            )
            exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
                exit_code,
                stdout_text,
                stderr_text,
                session if selector == "project_path" else None,
                log_path=_wfe_refresh_log_path if selector == "project_path" else None,
            )
            if _running_or_timed_out_response(exit_code, stdout_text):
                pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_REFRESHING)
                payload = _emit_running_payload("wait-for-exec", session, args.request_id, args, phase=PHASE_REFRESHING)
                _inject_log_range_into_payload(payload, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path), offsets_invalidated=_wfe_offsets_invalidated)
                return EXIT_RUNNING, emit_payload(payload), ""
            if exit_code != 0:
                _clear_pending_exec(args, args.request_id)
                stdout_text = _remap_request_id_in_response(
                    stdout_text,
                    args.request_id,
                    args,
                    phase=PHASE_REFRESHING,
                    normalize_compiling=False,
                )
                stderr_text = _remap_request_id_in_response(
                    stderr_text,
                    args.request_id,
                    args,
                    phase=PHASE_REFRESHING,
                    normalize_compiling=False,
                )
                exit_code, stdout_text, stderr_text = _normalize_exec_response(
                    exit_code,
                    stdout_text,
                    stderr_text,
                    args,
                    request_id=args.request_id,
                    default_phase=PHASE_REFRESHING,
                    normalize_compiling=False,
                )
                stdout_text = _inject_log_range_into_stdout(stdout_text, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path), offsets_invalidated=_wfe_offsets_invalidated)
                stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "wait-for-exec", args, request_id=args.request_id)
                return exit_code, stdout_text, stderr_text
            try:
                session = _ensure_project_session_ready_after_refresh(args)
                base_url = session.base_url
            except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
                pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_REFRESHING)
                payload = _emit_running_payload("wait-for-exec", exc.session, args.request_id, args, phase=PHASE_REFRESHING)
                _inject_log_range_into_payload(payload, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path), offsets_invalidated=_wfe_offsets_invalidated)
                return EXIT_RUNNING, emit_payload(payload), ""
            pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_EXECUTING)
        exit_code, stdout_text, stderr_text = _invoke_exec(
            base_url,
            args.request_id,
            pending["code"],
            pending["script_args_json"],
            args,
            source_path=pending.get("source_path"),
            import_base_url=pending.get("import_base_url"),
            reset_jsenv_before_exec=bool(pending.get("reset_jsenv_before_exec")),
            stale_module_policy=pending.get("stale_module_policy", STALE_MODULE_POLICY_AUTO_RESET),
        )
    else:
        payload = {
            "request_id": args.request_id,
            "wait_timeout_ms": args.wait_timeout_ms,
            "include_diagnostics": args.include_diagnostics,
        }
        exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
            "wait-for-exec",
            base_url,
            payload,
            args.wait_timeout_ms,
        )
    exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
        exit_code,
        stdout_text,
        stderr_text,
        session if selector == "project_path" else None,
        log_path=_wfe_log_path_early if selector == "project_path" else None,
    )
    if selector == "project_path" and pending is not None:
        pending = _finalize_pending_after_submit(args, args.request_id, pending, exit_code, stdout_text)
    default_phase = PHASE_COMPILING if _is_compiling_response(exit_code, stdout_text) else None
    exit_code, stdout_text, stderr_text = _normalize_exec_response(
        exit_code,
        stdout_text,
        stderr_text,
        args,
        request_id=args.request_id,
        default_phase=default_phase,
    )
    _wfe_final_log_path = _resolve_log_path(args, session)
    stdout_text = _inject_log_range_into_stdout(stdout_text, _wfe_final_log_path, _wfe_log_start, _capture_log_offset(_wfe_final_log_path), offsets_invalidated=_wfe_offsets_invalidated)
    stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "wait-for-exec", args, request_id=args.request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_for_compile(args):
    selector = resolve_selector(args)
    validate_positive(args.appear_timeout_seconds, "appear-timeout-seconds")
    validate_positive(args.settle_timeout_seconds, "settle-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")

    validate_project_mode_only(selector, "unity-exe-path", getattr(args, "unity_exe_path", None))
    validate_project_mode_only(selector, "unity-log-path", getattr(args, "unity_log_path", None))
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=getattr(args, "unity_exe_path", None),
            unity_log_path=getattr(args, "unity_log_path", None),
            unity_launch_args=getattr(args, "unity_launch_args", None),
            argv0=getattr(args, "argv0", None),
        )
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    cycle = wait_for_compile_cycle(
        base_url,
        args.appear_timeout_seconds,
        args.settle_timeout_seconds,
        args.health_timeout_seconds,
    )
    outcome = cycle["outcome"]
    diagnostics = {"observed_health": cycle["observed_health"]}

    if outcome == COMPILE_OUTCOME_READY:
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={"status": "compile_settled", "compile_observed": True},
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "completed", args)
        return 0, emit_payload(payload), ""

    if outcome == COMPILE_OUTCOME_NONE:
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={"status": "no_compile_observed", "compile_observed": False},
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "no_compile_observed", args)
        return 0, emit_payload(payload), ""

    # settle_timeout: an observed compile did not return to ready in time. Surface a
    # non-terminal running/timeout result rather than falsely reporting completion.
    payload = {
        "ok": True,
        "status": "running",
        "operation": "wait-for-compile",
        "phase": PHASE_COMPILING,
    }
    if session is not None:
        payload["session"] = session.to_payload()
    payload = attach_diagnostics(
        payload,
        include_diagnostics=args.include_diagnostics,
        session=session,
        diagnostics=diagnostics,
    )
    _attach_guidance(payload, "wait-for-compile", "running", args)
    return EXIT_RUNNING, emit_payload(payload), ""


def run_wait_for_log_pattern(args):
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_non_negative(args.start_offset, "start-offset")
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    try:
        re.compile(args.pattern)
    except re.error as exc:
        raise ValueError("invalid regex: {}".format(exc))

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
    else:
        session = unity_session.create_direct_session(args.base_url)

    if session is None:
        payload = expected_failure_payload(
            "wait-for-log-pattern",
            "no_observation_target",
            "no observable Unity log source is available",
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, "wait-for-log-pattern", "no_observation_target", args)
        return EXIT_NO_OBSERVATION_TARGET, emit_payload(payload), ""

    log_path = _resolve_log_path(args, session)
    log_start = args.start_offset if args.start_offset is not None else _capture_log_offset(log_path)
    offsets_invalidated = _detect_offset_invalidation(log_path, args.start_offset)

    try:
        session = unity_session.wait_for_log_pattern(
            session,
            args.pattern,
            args.timeout_seconds,
            activity_timeout_seconds=args.activity_timeout_seconds,
            health_timeout_seconds=args.health_timeout_seconds,
            start_offset=args.start_offset,
            extract_group=args.extract_group,
            extract_json_group=args.extract_json_group,
            expected_session_marker=args.expected_session_marker,
        )
    except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
        status = "unity_stalled" if isinstance(exc, unity_session.UnityStalledError) else "unity_not_ready"
        payload = expected_failure_payload(
            "wait-for-log-pattern",
            status,
            exc,
            session=exc.session,
            include_diagnostics=args.include_diagnostics,
        )
        _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
        _attach_guidance(payload, "wait-for-log-pattern", status, args)
        return EXIT_UNITY_NOT_READY, emit_payload(payload), ""

    result = {"status": "log_pattern_matched"}
    if args.extract_group is not None:
        result["extracted_group"] = session.diagnostics["extracted_group"]
    if args.extract_json_group is not None:
        result["extracted_json"] = session.diagnostics["extracted_json"]
    payload = success_payload(
        "wait-for-log-pattern",
        session=session,
        result=result,
        include_diagnostics=args.include_diagnostics,
    )
    _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
    return 0, emit_payload(payload), ""


def run_wait_for_result_marker(args):
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_non_negative(args.start_offset, "start-offset")
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
    else:
        session = unity_session.create_direct_session(args.base_url)

    if session is None:
        payload = expected_failure_payload(
            "wait-for-result-marker",
            "no_observation_target",
            "no observable Unity log source is available",
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, "wait-for-result-marker", "no_observation_target", args)
        return EXIT_NO_OBSERVATION_TARGET, emit_payload(payload), ""

    log_path = _resolve_log_path(args, session)
    log_start = args.start_offset if args.start_offset is not None else _capture_log_offset(log_path)
    offsets_invalidated = _detect_offset_invalidation(log_path, args.start_offset)

    deadline = time.time() + args.timeout_seconds
    while True:
        remaining = max(deadline - time.time(), 0.001)
        try:
            session = unity_session.wait_for_log_pattern(
                session,
                RESULT_MARKER_PATTERN,
                remaining,
                activity_timeout_seconds=args.activity_timeout_seconds,
                health_timeout_seconds=args.health_timeout_seconds,
                start_offset=args.start_offset,
                extract_group=1,
                expected_session_marker=args.expected_session_marker,
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            status = "unity_stalled" if isinstance(exc, unity_session.UnityStalledError) else "unity_not_ready"
            payload = expected_failure_payload(
                "wait-for-result-marker",
                status,
                exc,
                session=exc.session,
                include_diagnostics=args.include_diagnostics,
            )
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
            _attach_guidance(payload, "wait-for-result-marker", status, args)
            return EXIT_UNITY_NOT_READY, emit_payload(payload), ""

        marker_text = session.diagnostics.get("extracted_group")
        try:
            marker = json.loads(marker_text)
        except (TypeError, json.JSONDecodeError):
            marker = None
        if isinstance(marker, dict) and marker.get("correlation_id") == args.correlation_id:
            payload = success_payload(
                "wait-for-result-marker",
                session=session,
                result={
                    "status": "result_marker_matched",
                    "marker": marker,
                },
                include_diagnostics=args.include_diagnostics,
            )
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
            return 0, emit_payload(payload), ""
        next_offset = session.diagnostics.get("matched_log_offset")
        args.start_offset = next_offset
        if next_offset is None:
            raise RuntimeError("result marker wait matched without a follow-up offset")


def run_get_log_source(args):
    selector = resolve_selector(args)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    if selector == "project_path":
        source = unity_session.get_log_source(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
    else:
        source = unity_session.get_log_source(base_url=args.base_url)

    if source is None:
        payload = expected_failure_payload(
            "get-log-source",
            "no_observation_target",
            "no observable Unity log source is available",
            include_diagnostics=args.include_diagnostics,
        )
        return EXIT_NO_OBSERVATION_TARGET, emit_payload(payload), ""

    session, result = source
    payload = success_payload(
        "get-log-source",
        session=session,
        result=result,
        include_diagnostics=args.include_diagnostics,
    )
    return 0, emit_payload(payload), ""


def run_get_blocker_state(args):
    session = unity_session.get_blocker_state(project_path=args.project_path, argv0=getattr(args, "argv0", None))
    blocker = _detect_exec_modal_blocker(session)
    if blocker is None:
        payload = success_payload(
            "get-blocker-state",
            session=session,
            result={"status": "no_blocker"},
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, "get-blocker-state", "completed", args)
        return 0, emit_payload(payload), ""

    payload = success_payload(
        "get-blocker-state",
        session=session,
        result={"status": "modal_blocked", "blocker": blocker},
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(payload, "get-blocker-state", "completed", args)
    return 0, emit_payload(payload), ""


def run_resolve_blocker(args):
    if sys.platform != "win32" or not args.project_path:
        payload = {
            "ok": False,
            "status": "unsupported_operation",
            "operation": "resolve-blocker",
            "error": "windows_project_path_required",
        }
        return 1, emit_payload(payload), ""

    session = unity_session.get_blocker_state(project_path=args.project_path, argv0=getattr(args, "argv0", None))
    result = unity_modal_blockers.resolve_modal_blocker(session.unity_pid, action=args.action)
    if result.get("ok"):
        payload = success_payload(
            "resolve-blocker",
            session=session,
            result=result["result"],
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, "resolve-blocker", "completed", args)
        return 0, emit_payload(payload), ""

    payload = {"ok": False, "status": result["status"], "operation": "resolve-blocker"}
    if session is not None:
        payload["session"] = session.to_payload()
    if "action" in result:
        payload["action"] = result["action"]
    if "blocker" in result:
        payload["blocker"] = result["blocker"]
    if "error" in result:
        payload["error"] = result["error"]
    payload = attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)
    _attach_guidance(payload, "resolve-blocker", result["status"], args)
    return 1, emit_payload(payload), ""


def run_get_log_briefs(args):
    range_str = args.range_str
    sep = "," if "," in range_str and "-" not in range_str.lstrip("-") else "-"
    if "," in range_str:
        parts = range_str.split(",", 1)
    else:
        # Handle START-END where END could also be negative; use last hyphen as separator
        idx = range_str.rfind("-")
        if idx <= 0:
            raise ValueError("--range must be START-END or START,END")
        parts = [range_str[:idx], range_str[idx + 1:]]
    try:
        range_start = int(parts[0])
        range_end = int(parts[1])
    except (ValueError, IndexError):
        raise ValueError("--range must contain integer start and end offsets")

    levels = None
    if args.levels:
        levels = [lv.strip() for lv in args.levels.split(",") if lv.strip()]

    indexes_str = getattr(args, "indexes_str", None)
    include_str = getattr(args, "include_str", None)
    _INDEXES_FORMAT_ERROR = (
        "--indexes must be comma-separated 1-based brief indices, e.g. `--indexes 3,5`, "
        "corresponding to `brief_sequence` positions"
    )

    def _parse_indexes(raw):
        try:
            return [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise ValueError(_INDEXES_FORMAT_ERROR)

    include_indices = None
    if indexes_str and include_str:
        parsed_indexes = _parse_indexes(indexes_str)
        parsed_include = _parse_indexes(include_str)
        if parsed_indexes != parsed_include:
            raise ValueError(
                "--indexes and --include were both supplied with different values; "
                "supply only one, or make them match",
                "conflicting_indexes_include",
            )
        include_indices = parsed_indexes
    elif indexes_str or include_str:
        include_indices = _parse_indexes(indexes_str or include_str)

    full_text = getattr(args, "full_text", False)
    if full_text and not include_indices:
        raise ValueError(
            "--full-text requires --indexes (or its --include alias) with one or more explicit 1-based brief indices",
            "full_text_requires_include",
        )

    log_path = getattr(args, "unity_log_path", None)
    if log_path is None and getattr(args, "project_path", None):
        source = unity_session.get_log_source(project_path=args.project_path, argv0=getattr(args, "argv0", None))
        if source is not None:
            log_path = source[0].effective_log_path
    if log_path is None:
        log_path = str(unity_session_logs.default_editor_log_path())

    briefs = unity_log_brief.parse_log_briefs(log_path, range_start, range_end)
    filtered = unity_log_brief.filter_briefs(briefs, levels=levels, include_indices=include_indices)
    if full_text:
        selected_indices = set(include_indices or ())
        for brief in filtered:
            if brief.get("index") in selected_indices:
                brief["full_text"] = unity_log_brief.full_text_for_brief(log_path, brief)

    payload = success_payload(
        "get-log-briefs",
        result=filtered,
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(payload, "get-log-briefs", "completed", args)
    return 0, emit_payload(payload), ""


def _run_get_compile_messages(args, command_name):
    """Shared implementation for get-compile-errors / get-compile-warnings."""
    selector = resolve_selector(args)
    validate_non_negative(args.start, "start")
    if args.count < 1 or args.count > 100:
        raise ValueError("count must be between 1 and 100")
    validate_project_mode_only(selector, "unity-exe-path", getattr(args, "unity_exe_path", None))
    validate_project_mode_only(selector, "unity-log-path", getattr(args, "unity_log_path", None))
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=getattr(args, "unity_exe_path", None),
            unity_log_path=getattr(args, "unity_log_path", None),
            unity_launch_args=getattr(args, "unity_launch_args", None),
            argv0=getattr(args, "argv0", None),
        )
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    payload = {"start": args.start, "count": args.count}
    exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
        command_name,
        base_url,
        payload,
        5000,
    )
    if exit_code != 0:
        stdout_text, stderr_text = _inject_guidance_into_response(
            stdout_text, stderr_text, command_name, args
        )
        return exit_code, stdout_text, stderr_text
    body = json.loads(stdout_text)
    result = {
        "total": body.get("total", 0),
        "start": body.get("start", 0),
        "returned": body.get("returned", 0),
        "messages": body.get("messages", []),
        "session_marker": body.get("session_marker", ""),
    }
    response = success_payload(
        command_name,
        session=session,
        result=result,
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(response, command_name, "completed", args)
    return 0, emit_payload(response), ""


def run_get_compile_errors(args):
    return _run_get_compile_messages(args, "get-compile-errors")


def run_get_compile_warnings(args):
    return _run_get_compile_messages(args, "get-compile-warnings")


def run_ensure_stopped(args):
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")

    mode = "inspect"
    if args.immediate_kill:
        mode = "immediate_kill"
    elif not args.inspect_only:
        mode = "timeout_then_kill"

    if selector == "base_url" and args.immediate_kill:
        raise ValueError("immediate-kill is only valid with --project-path")

    if selector == "project_path":
        stopped, session = unity_session.ensure_stopped(project_path=args.project_path, mode=mode, timeout_seconds=args.timeout_seconds, argv0=getattr(args, "argv0", None))
    else:
        stopped, session = unity_session.ensure_stopped(base_url=args.base_url, mode="inspect", timeout_seconds=args.timeout_seconds)

    if not stopped:
        payload = expected_failure_payload(
            "ensure-stopped",
            "not_stopped",
            "target is not stopped",
            session=session,
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, "ensure-stopped", "not_stopped", args)
        return EXIT_NOT_STOPPED, emit_payload(payload), ""

    payload = success_payload(
        "ensure-stopped",
        session=session,
        result={"status": "stopped"},
        include_diagnostics=args.include_diagnostics,
    )
    return 0, emit_payload(payload), ""


def attach_diagnostics(payload, include_diagnostics=False, session=None, diagnostics=None):
    if not include_diagnostics:
        payload.pop("diagnostics", None)
        return payload
    merged = {}
    if session is not None and session.diagnostics:
        merged.update(session.diagnostics)
    if diagnostics:
        merged.update(diagnostics)
    if merged:
        payload["diagnostics"] = merged
    return payload




def _extract_compile_errors_from_log(log_path, max_errors=20):
    """Extract C# compile errors from a Unity Editor log file."""
    import re
    if not log_path:
        return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return None
    # Matches: file(line,col): error [CODE]: message
    # Error code (e.g. CS1003) is optional; some Unity errors omit it.
    # The +? on the file path is non-greedy so paths with parentheses still match.
    error_pattern = re.compile(
        r"^(.+?)\((\d+),(\d+)\):\s*error\s+(?:([A-Z]+\d+):\s*)?(.+)$"
    )
    errors = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n\r")
        m = error_pattern.match(line)
        if m:
            filepath = m.group(1)
            line_no = int(m.group(2))
            col = int(m.group(3))
            code = m.group(4)  # may be None for uncoded errors
            msg = m.group(5)
            # Strip leading ": " when no error code was matched
            if msg and msg.startswith(": "):
                msg = msg[2:]
            # Collect continuation lines (indented, not a new error)
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")) and not error_pattern.match(lines[i].strip()):
                continuation = lines[i].rstrip("\n\r")
                if continuation.strip():
                    msg += "\n" + continuation.strip()
                i += 1
            errors.append({
                "file": filepath,
                "line": line_no,
                "column": col,
                "code": code or None,
                "message": msg,
            })
        else:
            i += 1
    if not errors:
        return None
    return {
        "total_errors": len(errors),
        "errors": errors[:max_errors],
    }


def _bring_unity_to_foreground(session):
    """Bring the Unity Editor main window to foreground so it detects file changes."""
    if session is None or not session.unity_pid:
        return
    if sys.platform != "win32":
        return
    try:
        unity_modal_blockers._foreground_unity_window(session.unity_pid)
    except Exception:
        pass

def _normalize_exec_blocker_result(exit_code, stdout_text, stderr_text, session, log_path=None):
    if session is None or not stdout_text:
        return exit_code, stdout_text, stderr_text
    body = json.loads(stdout_text)
    if not _should_check_exec_blocker(exit_code, body):
        return exit_code, stdout_text, stderr_text
    blocker = _detect_exec_modal_blocker(session)
    if blocker is None:
        return exit_code, stdout_text, stderr_text

    # Safe Mode: auto-dismiss and return as compile errors so Agent never sees modal_blocked
    if blocker.get("type") == "safe_mode_dialog":
        # Auto-click "Enter Safe Mode" if the dialog is still showing
        try:
            resolve_result = unity_modal_blockers.resolve_modal_blocker(
                session.unity_pid, action="cancel", timeout_ms=3000
            )
        except Exception:
            resolve_result = {"ok": False}
        # Extract compile errors from log
        compile_info = _extract_compile_errors_from_log(log_path) if log_path else None
        normalized = {
            "ok": False,
            "status": "unity_compile_error",
            "request_id": body.get("request_id"),
            "compile_errors_total": 0,
            "compile_warnings_total": 0,
            "compile_messages": [],
        }
        if compile_info:
            normalized["compile_errors_total"] = compile_info["total_errors"]
            normalized["compile_messages"] = compile_info["errors"]
        if "diagnostics" in body:
            normalized["diagnostics"] = body["diagnostics"]
        return direct_exec_client.EXIT_UNITY_COMPILE_ERROR, emit_payload(normalized), ""

    # Other modal blockers: report as before
    normalized = {
        "ok": False,
        "status": "modal_blocked",
        "request_id": body.get("request_id"),
        "blocker": blocker,
    }
    if "diagnostics" in body:
        normalized["diagnostics"] = body["diagnostics"]
    return EXIT_MODAL_BLOCKED, emit_payload(normalized), ""


def _should_check_exec_blocker(exit_code, body):
    status = body.get("status")
    if exit_code == EXIT_NOT_AVAILABLE and status == "not_available" and body.get("error") == "timed out":
        return True
    if status == "running":
        return True
    return False


def _detect_exec_modal_blocker(session):
    if session is None or session.unity_pid is None:
        return None
    return unity_modal_blockers.detect_modal_blocker(session.unity_pid, scope="exec")
