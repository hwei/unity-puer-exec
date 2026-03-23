#!/usr/bin/env python3
import json
import re
import sys
import time
import uuid

import direct_exec_client
import unity_modal_blockers
import unity_session


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


def emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


def usage_error(message, status="failed"):
    payload = {"ok": False, "status": status, "error": message}
    if status == "address_conflict":
        return 2, emit_payload(payload), ""
    return 2, "", emit_payload(payload)


def validate_positive(value, name):
    if value is not None and value <= 0:
        raise ValueError("{} must be positive".format(name))


def validate_non_negative(value, name):
    if value is not None and value < 0:
        raise ValueError("{} must be non-negative".format(name))


def validate_project_mode_only(selector, option_name, value):
    if selector == "base_url" and value:
        raise ValueError("{} is only valid with --project-path".format(option_name))


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
        return run_ensure_stopped(args)
    except ValueError as exc:
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
        return EXIT_UNITY_START_FAILED, emit_payload(payload), ""
    except unity_session.UnityLaunchConflictError as exc:
        payload = expected_failure_payload(
            args.command,
            "launch_conflict",
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
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
        return EXIT_UNITY_NOT_READY, emit_payload(payload), ""
    except unity_session.UnitySessionStateError as exc:
        payload = expected_failure_payload(
            args.command,
            exc.status,
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        return EXIT_SESSION_STATE, emit_payload(payload), ""
    except Exception as exc:  # noqa: BLE001 - CLI should normalize unexpected failures.
        payload = unexpected_failure_payload(
            args.command,
            exc,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        return 1, emit_payload(payload), ""


def run_cli(argv, surface):
    help_result = surface.handle_top_level_help(argv)
    if help_result is not None:
        return help_result
    help_result = surface.handle_command_help(argv)
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


def _next_step_payload(args, request_id):
    project_path = _project_path_arg(args)
    argv = [
        "unity-puer-exec",
        "wait-for-exec",
        "--project-path",
        project_path,
        "--request-id",
        request_id,
        "--wait-timeout-ms",
        str(args.wait_timeout_ms),
    ]
    if getattr(args, "unity_exe_path", None):
        argv.extend(["--unity-exe-path", args.unity_exe_path])
    if getattr(args, "unity_log_path", None):
        argv.extend(["--unity-log-path", args.unity_log_path])
    if getattr(args, "include_log_offset", False):
        argv.append("--include-log-offset")
    if getattr(args, "include_diagnostics", False):
        argv.append("--include-diagnostics")
    return {"command": "wait-for-exec", "argv": argv}


def _pending_exec_payload(request_id, code):
    return {"request_id": request_id, "code": code}


def _write_pending_exec(args, request_id, code):
    unity_session.write_pending_exec_artifact(
        _project_path_arg(args),
        request_id,
        _pending_exec_payload(request_id, code),
    )


def _read_pending_exec(args, request_id):
    return unity_session.read_pending_exec_artifact(_project_path_arg(args), request_id)


def _clear_pending_exec(args, request_id):
    unity_session.clear_pending_exec_artifact(_project_path_arg(args), request_id)


def _emit_running_startup_payload(operation, session, request_id, args):
    payload = {
        "ok": True,
        "status": "running",
        "operation": operation,
        "request_id": request_id,
        "next_step": _next_step_payload(args, request_id),
    }
    if session is not None:
        payload["session"] = session.to_payload()
    return attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)


def _invoke_exec(base_url, request_id, code, args):
    payload = {
        "request_id": request_id,
        "code": code,
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_log_offset": args.include_log_offset,
        "include_diagnostics": args.include_diagnostics,
    }
    return direct_exec_client.invoke_command(
        "exec",
        base_url,
        payload,
        args.wait_timeout_ms,
    )


def _normalize_exec_response(stdout_text, stderr_text, args):
    if stdout_text:
        body = json.loads(stdout_text)
        if body.get("status") == "running" and getattr(args, "project_path", None):
            body["next_step"] = _next_step_payload(args, body.get("request_id"))
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stdout_text = emit_payload(body)
    if stderr_text:
        body = json.loads(stderr_text)
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stderr_text = emit_payload(body)
    return stdout_text, stderr_text


def _should_keep_pending_after_submit(exit_code, stdout_text):
    if not stdout_text:
        return False
    body = json.loads(stdout_text)
    status = body.get("status")
    return exit_code == EXIT_NOT_AVAILABLE and status == "not_available"


def run_exec(args):
    request_id = args.request_id or uuid.uuid4().hex
    code = read_exec_code(args)
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            _write_pending_exec(args, request_id, code)
            payload = _emit_running_startup_payload("exec", exc.session, request_id, args)
            return EXIT_RUNNING, emit_payload(payload), ""
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    exit_code, stdout_text, stderr_text = _invoke_exec(base_url, request_id, code, args)
    exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
        exit_code,
        stdout_text,
        stderr_text,
        session if selector == "project_path" else None,
    )
    if selector == "project_path" and not _should_keep_pending_after_submit(exit_code, stdout_text):
        _clear_pending_exec(args, request_id)
    stdout_text, stderr_text = _normalize_exec_response(stdout_text, stderr_text, args)
    return exit_code, stdout_text, stderr_text


def run_wait_for_exec(args):
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            if _read_pending_exec(args, args.request_id) is not None:
                payload = _emit_running_startup_payload("wait-for-exec", exc.session, args.request_id, args)
                return EXIT_RUNNING, emit_payload(payload), ""
            raise
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    pending = _read_pending_exec(args, args.request_id) if selector == "project_path" else None
    if pending is not None:
        exit_code, stdout_text, stderr_text = _invoke_exec(base_url, args.request_id, pending["code"], args)
    else:
        payload = {
            "request_id": args.request_id,
            "wait_timeout_ms": args.wait_timeout_ms,
            "include_log_offset": args.include_log_offset,
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
    if selector == "project_path" and pending is not None and not _should_keep_pending_after_submit(exit_code, stdout_text):
        _clear_pending_exec(args, args.request_id)
    stdout_text, stderr_text = _normalize_exec_response(stdout_text, stderr_text, args)
    return exit_code, stdout_text, stderr_text


def run_wait_until_ready(args):
    selector = resolve_selector(args)
    validate_positive(args.ready_timeout_seconds, "ready-timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

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

    payload = success_payload(
        "wait-until-ready",
        session=session,
        result={"status": "recovered"},
        include_diagnostics=args.include_diagnostics,
    )
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
        return EXIT_NO_OBSERVATION_TARGET, emit_payload(payload), ""

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
        return EXIT_NO_OBSERVATION_TARGET, emit_payload(payload), ""

    deadline = time.time() + args.timeout_seconds
    while True:
        remaining = max(deadline - time.time(), 0.001)
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
        return 0, emit_payload(payload), ""

    payload = success_payload(
        "get-blocker-state",
        session=session,
        result={"status": "modal_blocked", "blocker": blocker},
        include_diagnostics=args.include_diagnostics,
    )
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
    return 1, emit_payload(payload), ""


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
