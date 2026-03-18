#!/usr/bin/env python3
import json
import re
import sys
import time
import uuid

import direct_exec_client
import unity_session


EXIT_RUNNING = direct_exec_client.EXIT_RUNNING
EXIT_COMPILING = direct_exec_client.EXIT_COMPILING
EXIT_NOT_AVAILABLE = direct_exec_client.EXIT_NOT_AVAILABLE
EXIT_MISSING = direct_exec_client.EXIT_MISSING
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
        if args.command == "wait-for-log-pattern":
            return run_wait_for_log_pattern(args)
        if args.command == "wait-for-result-marker":
            return run_wait_for_result_marker(args)
        if args.command == "get-log-source":
            return run_get_log_source(args)
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


def run_exec(args):
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=args.unity_exe_path,
            unity_log_path=args.unity_log_path,
        )
        base_url = session.base_url
    else:
        base_url = args.base_url

    payload = {
        "id": uuid.uuid4().hex,
        "code": read_exec_code(args),
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_log_offset": args.include_log_offset,
        "include_diagnostics": args.include_diagnostics,
    }
    exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
        "exec",
        base_url,
        payload,
        args.wait_timeout_ms,
    )
    if stdout_text:
        body = json.loads(stdout_text)
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stdout_text = emit_payload(body)
    if stderr_text:
        body = json.loads(stderr_text)
        if not args.include_diagnostics:
            body.pop("diagnostics", None)
        stderr_text = emit_payload(body)
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
