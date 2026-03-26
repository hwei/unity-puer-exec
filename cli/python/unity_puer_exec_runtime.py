#!/usr/bin/env python3
import json
import re
import sys
import time
import uuid

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
EXIT_SESSION_STATE = 14
EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21
RESULT_MARKER_PREFIX = "[UnityPuerExecResult]"
RESULT_MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"
PHASE_REFRESHING = "refreshing"
PHASE_COMPILING = "compiling"
PHASE_EXECUTING = "executing"
REFRESH_BEFORE_EXEC_TEMPLATE = """export default function run(ctx) {
  const AssetDatabase = puer.loadType('UnityEditor.AssetDatabase');
  AssetDatabase.Refresh();
  return { request_id: ctx.request_id, refreshed: true };
}
"""


def emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


def usage_error(message, status="failed"):
    payload = {"ok": False, "status": status, "error": message}
    if status == "address_conflict":
        return 2, emit_payload(payload), ""
    return 2, "", emit_payload(payload)


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


def _inject_log_range_into_stdout(stdout_text, log_path, log_start, log_end):
    if not stdout_text:
        return stdout_text
    body = json.loads(stdout_text)
    body["log_range"] = {"start": log_start, "end": log_end}
    briefs = unity_log_brief.parse_log_briefs(log_path, log_start, log_end)
    body["brief_sequence"] = unity_log_brief.build_brief_sequence(briefs)
    return emit_payload(body)


def _inject_log_range_into_payload(payload, log_path, log_start, log_end):
    payload["log_range"] = {"start": log_start, "end": log_end}
    briefs = unity_log_brief.parse_log_briefs(log_path, log_start, log_end)
    payload["brief_sequence"] = unity_log_brief.build_brief_sequence(briefs)


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


def run_command(args):
    try:
        if args.command == "exec":
            return run_exec(args)
        if args.command == "wait-until-ready":
            return run_wait_until_ready(args)
        if args.command == "wait-for-exec":
            return run_wait_for_exec(args)
        if args.command == "wait-for-log-pattern":
            return run_wait_for_log_pattern(args)
        if args.command == "wait-for-result-marker":
            return run_wait_for_result_marker(args)
        if args.command == "get-log-source":
            return run_get_log_source(args)
        if args.command == "get-blocker-state":
            return run_get_blocker_state(args)
        if args.command == "resolve-blocker":
            return run_resolve_blocker(args)
        if args.command == "get-log-briefs":
            return run_get_log_briefs(args)
        return run_ensure_stopped(args)
    except ValueError as exc:
        if len(exc.args) >= 2 and isinstance(exc.args[1], str):
            return usage_error(str(exc.args[0]), status=exc.args[1])
        status = "address_conflict" if str(exc) == "address_conflict" else "failed"
        return usage_error(str(exc), status=status)
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


def run_cli(argv, surface):
    filtered_argv = [a for a in argv if a != "--suppress-guidance"]
    help_result = surface.handle_top_level_help(filtered_argv)
    if help_result is not None:
        return help_result
    help_result = surface.handle_command_help(filtered_argv)
    if help_result is not None:
        return help_result
    parser = surface.build_parser()
    args = parser.parse_args(argv)
    return run_command(args)


def read_exec_code(args):
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    return args.code


def _project_path_arg(args):
    return str(unity_session.resolve_project_path(getattr(args, "project_path", None)))


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
    if getattr(args, "include_diagnostics", False):
        context["include_diagnostics"] = True
    return context


def _attach_guidance(payload, command, status, args, request_id=None):
    if getattr(args, "suppress_guidance", False):
        return
    context = _build_guidance_context(args, request_id=request_id)
    next_steps = help_surface.build_next_steps(command, status, context)
    if next_steps:
        payload["next_steps"] = next_steps
    situation = help_surface.build_situation(command, status)
    if situation:
        payload["situation"] = situation


def _inject_guidance_into_stdout(stdout_text, command, args, request_id=None):
    if not stdout_text or getattr(args, "suppress_guidance", False):
        return stdout_text
    body = json.loads(stdout_text)
    rid = request_id or body.get("request_id")
    _attach_guidance(body, command, body.get("status"), args, request_id=rid)
    return emit_payload(body)


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
):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args": script_args,
        "script_args_json": script_args_json,
        "refresh_before_exec": bool(refresh_before_exec),
    }
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


def _invoke_exec(base_url, request_id, code, script_args_json, args):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args_json": script_args_json,
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_diagnostics": args.include_diagnostics,
    }
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
        ready_timeout_seconds=_post_refresh_ready_timeout_seconds(args),
    )


def _refresh_exec_code():
    return REFRESH_BEFORE_EXEC_TEMPLATE


def _invoke_refresh_exec(base_url, request_id, args):
    return _invoke_exec(base_url, request_id, _refresh_exec_code(), "{}", args)


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


def run_exec(args):
    if getattr(args, "include_log_offset", False):
        return usage_error("--include-log-offset has been removed; use log_range.start from exec response")
    request_id = args.request_id or uuid.uuid4().hex
    code = read_exec_code(args)
    script_args, script_args_json = _canonicalize_script_args(getattr(args, "script_args", None))
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    validate_project_mode_only(selector, "refresh-before-exec", getattr(args, "refresh_before_exec", False))

    if selector == "project_path":
        _sweep_pending_exec(args)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            _write_pending_exec(
                args,
                request_id,
                code,
                script_args,
                script_args_json,
                refresh_before_exec=args.refresh_before_exec,
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
        )
        exit_code, stdout_text, stderr_text = _invoke_refresh_exec(base_url, refresh_request_id, args)
        exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
            exit_code,
            stdout_text,
            stderr_text,
            session,
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
            stdout_text = _inject_guidance_into_stdout(stdout_text, "exec", args, request_id=request_id)
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

    exit_code, stdout_text, stderr_text = _invoke_exec(base_url, request_id, code, script_args_json, args)
    exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
        exit_code,
        stdout_text,
        stderr_text,
        session if selector == "project_path" else None,
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
    stdout_text = _inject_guidance_into_stdout(stdout_text, "exec", args, request_id=request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_for_exec(args):
    if getattr(args, "include_log_offset", False):
        return usage_error("--include-log-offset has been removed; use log_range.start from exec response")
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    _wfe_log_path_early = getattr(args, "unity_log_path", None) or str(unity_session_logs.default_editor_log_path())
    _wfe_log_start = args.log_start_offset if args.log_start_offset is not None else _capture_log_offset(_wfe_log_path_early)

    if selector == "project_path":
        _sweep_pending_exec(args)
        pending = _read_pending_exec(args, args.request_id)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
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
                _inject_log_range_into_payload(payload, _wfe_rp1_log_path, _wfe_log_start, _capture_log_offset(_wfe_rp1_log_path))
                return EXIT_RUNNING, emit_payload(payload), ""
            raise
        base_url = session.base_url
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
            )
            if _running_or_timed_out_response(exit_code, stdout_text):
                pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_REFRESHING)
                payload = _emit_running_payload("wait-for-exec", session, args.request_id, args, phase=PHASE_REFRESHING)
                _inject_log_range_into_payload(payload, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path))
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
                stdout_text = _inject_log_range_into_stdout(stdout_text, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path))
                stdout_text = _inject_guidance_into_stdout(stdout_text, "wait-for-exec", args, request_id=args.request_id)
                return exit_code, stdout_text, stderr_text
            try:
                session = _ensure_project_session_ready_after_refresh(args)
                base_url = session.base_url
            except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
                pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_REFRESHING)
                payload = _emit_running_payload("wait-for-exec", exc.session, args.request_id, args, phase=PHASE_REFRESHING)
                _inject_log_range_into_payload(payload, _wfe_refresh_log_path, _wfe_log_start, _capture_log_offset(_wfe_refresh_log_path))
                return EXIT_RUNNING, emit_payload(payload), ""
            pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_EXECUTING)
        exit_code, stdout_text, stderr_text = _invoke_exec(
            base_url,
            args.request_id,
            pending["code"],
            pending["script_args_json"],
            args,
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
    stdout_text = _inject_log_range_into_stdout(stdout_text, _wfe_final_log_path, _wfe_log_start, _capture_log_offset(_wfe_final_log_path))
    stdout_text = _inject_guidance_into_stdout(stdout_text, "wait-for-exec", args, request_id=args.request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_until_ready(args):
    selector = resolve_selector(args)
    validate_positive(args.ready_timeout_seconds, "ready-timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_non_negative(args.start_offset, "start-offset")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    log_path = _resolve_log_path(args, None)
    log_start = args.start_offset if args.start_offset is not None else _capture_log_offset(log_path)

    try:
        if selector == "project_path":
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                ready_timeout_seconds=args.ready_timeout_seconds,
                activity_timeout_seconds=args.activity_timeout_seconds,
                health_timeout_seconds=args.health_timeout_seconds,
                unity_log_path=args.unity_log_path,
            )
        else:
            session = unity_session.create_direct_session(args.base_url)
            session = unity_session.wait_until_recovered(
                session,
                args.ready_timeout_seconds,
                activity_timeout_seconds=args.activity_timeout_seconds,
                health_timeout_seconds=args.health_timeout_seconds,
            )
    except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
        status = "unity_stalled" if isinstance(exc, unity_session.UnityStalledError) else "unity_not_ready"
        exc_log_path = _resolve_log_path(args, exc.session)
        payload = expected_failure_payload(
            "wait-until-ready",
            status,
            exc,
            session=exc.session,
            include_diagnostics=args.include_diagnostics,
        )
        _inject_log_range_into_payload(payload, exc_log_path, log_start, _capture_log_offset(exc_log_path))
        _attach_guidance(payload, "wait-until-ready", status, args)
        return EXIT_UNITY_NOT_READY, emit_payload(payload), ""

    log_path = _resolve_log_path(args, session)
    payload = success_payload(
        "wait-until-ready",
        session=session,
        result={"status": "recovered"},
        include_diagnostics=args.include_diagnostics,
    )
    _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
    _attach_guidance(payload, "wait-until-ready", "completed", args)
    return 0, emit_payload(payload), ""


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
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path)
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
        _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
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
    _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
    return 0, emit_payload(payload), ""


def run_wait_for_result_marker(args):
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_non_negative(args.start_offset, "start-offset")
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path)
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
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
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
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
            return 0, emit_payload(payload), ""
        next_offset = session.diagnostics.get("matched_log_offset")
        args.start_offset = next_offset
        if next_offset is None:
            raise RuntimeError("result marker wait matched without a follow-up offset")


def run_get_log_source(args):
    selector = resolve_selector(args)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    if selector == "project_path":
        source = unity_session.get_log_source(project_path=args.project_path, unity_log_path=args.unity_log_path)
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
    session = unity_session.get_blocker_state(project_path=args.project_path)
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

    session = unity_session.get_blocker_state(project_path=args.project_path)
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

    include_indices = None
    if args.include_str:
        try:
            include_indices = [int(x.strip()) for x in args.include_str.split(",") if x.strip()]
        except ValueError:
            raise ValueError("--include must be comma-separated integers")

    log_path = getattr(args, "unity_log_path", None)
    if log_path is None and getattr(args, "project_path", None):
        source = unity_session.get_log_source(project_path=args.project_path)
        if source is not None:
            log_path = source[0].effective_log_path
    if log_path is None:
        log_path = str(unity_session_logs.default_editor_log_path())

    briefs = unity_log_brief.parse_log_briefs(log_path, range_start, range_end)
    filtered = unity_log_brief.filter_briefs(briefs, levels=levels, include_indices=include_indices)

    payload = success_payload(
        "get-log-briefs",
        result=filtered,
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(payload, "get-log-briefs", "completed", args)
    return 0, emit_payload(payload), ""


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
        stopped, session = unity_session.ensure_stopped(project_path=args.project_path, mode=mode, timeout_seconds=args.timeout_seconds)
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


def _normalize_exec_blocker_result(exit_code, stdout_text, stderr_text, session):
    if session is None or not stdout_text:
        return exit_code, stdout_text, stderr_text
    body = json.loads(stdout_text)
    if not _should_check_exec_blocker(exit_code, body):
        return exit_code, stdout_text, stderr_text
    blocker = _detect_exec_modal_blocker(session)
    if blocker is None:
        return exit_code, stdout_text, stderr_text
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
