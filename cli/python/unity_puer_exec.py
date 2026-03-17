#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
import uuid

import direct_exec_client
import help_surface
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
HELP_FLAGS = ("--help", "--help-args", "--help-status")
RESULT_MARKER_PREFIX = "[UnityPuerExecResult]"
RESULT_MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"


def _build_parser():
    parser = argparse.ArgumentParser(prog="unity-puer-exec", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ready_parser = subparsers.add_parser("wait-until-ready", add_help=False)
    _add_selector_args(ready_parser)
    ready_parser.add_argument("--unity-exe-path", default=None)
    ready_parser.add_argument("--ready-timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)

    wait_log_parser = subparsers.add_parser("wait-for-log-pattern", add_help=False)
    _add_selector_args(wait_log_parser)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument("--start-offset", type=int, default=None)
    wait_log_parser.add_argument("--expected-session-marker", default=None)
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    extract_mode = wait_log_parser.add_mutually_exclusive_group()
    extract_mode.add_argument("--extract-group", type=int, default=None)
    extract_mode.add_argument("--extract-json-group", type=int, default=None)

    get_log_source_parser = subparsers.add_parser("get-log-source", add_help=False)
    _add_selector_args(get_log_source_parser)

    exec_parser = subparsers.add_parser("exec", add_help=False)
    _add_selector_args(exec_parser)
    exec_parser.add_argument("--unity-exe-path", default=None)
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    exec_parser.add_argument("--include-log-offset", action="store_true")
    script_source = exec_parser.add_mutually_exclusive_group(required=True)
    script_source.add_argument("--file", dest="file_path")
    script_source.add_argument("--stdin", action="store_true")
    script_source.add_argument("--code")

    wait_result_parser = subparsers.add_parser("wait-for-result-marker", add_help=False)
    _add_selector_args(wait_result_parser)
    wait_result_parser.add_argument("--correlation-id", required=True)
    wait_result_parser.add_argument("--start-offset", type=int, default=None)
    wait_result_parser.add_argument("--expected-session-marker", default=None)
    wait_result_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)

    ensure_stopped_parser = subparsers.add_parser("ensure-stopped", add_help=False)
    _add_selector_args(ensure_stopped_parser)
    ensure_stopped_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_STOP_TIMEOUT_SECONDS)
    stop_mode = ensure_stopped_parser.add_mutually_exclusive_group()
    stop_mode.add_argument("--inspect-only", action="store_true")
    stop_mode.add_argument("--immediate-kill", action="store_true")

    return parser


def _add_selector_args(parser):
    parser.add_argument("--project-path", default=None)
    parser.add_argument("--base-url", default=None)


def _emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


def _usage_text_error(message):
    return 2, "", message


def _usage_error(message, status="failed"):
    payload = {"ok": False, "status": status, "error": message}
    if status == "address_conflict":
        return 2, _emit_payload(payload), ""
    return 2, "", _emit_payload(payload)


def _validate_positive(value, name):
    if value is not None and value <= 0:
        raise ValueError("{} must be positive".format(name))


def _validate_non_negative(value, name):
    if value is not None and value < 0:
        raise ValueError("{} must be non-negative".format(name))


def _validate_project_mode_only(selector, option_name, value):
    if selector == "base_url" and value:
        raise ValueError("{} is only valid with --project-path".format(option_name))


def _resolve_selector(args):
    if getattr(args, "project_path", None) and getattr(args, "base_url", None):
        raise ValueError("address_conflict")
    if getattr(args, "base_url", None):
        return "base_url"
    return "project_path"


def _expected_execution_payload(status, error=None):
    payload = {"ok": False, "status": status}
    if error is not None:
        payload["error"] = str(error)
    return payload


def _success_payload(operation, session=None, result=None):
    payload = {"ok": True, "status": "completed", "operation": operation}
    if session is not None:
        payload["session"] = session.to_payload()
    if result is not None:
        payload["result"] = result
    return payload


def _expected_failure_payload(operation, status, error, session=None):
    payload = {"ok": False, "status": status, "operation": operation, "error": str(error)}
    if session is not None:
        payload["session"] = session.to_payload()
    return payload


def _unexpected_failure_payload(operation, error, session=None):
    payload = {"ok": False, "status": "failed", "operation": operation, "error": str(error)}
    if session is not None:
        payload["session"] = session.to_payload()
    return payload


def _read_exec_code(args):
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    return args.code


def _run_exec(args):
    selector = _resolve_selector(args)
    _validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    _validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=args.unity_exe_path,
        )
        base_url = session.base_url
    else:
        base_url = args.base_url

    payload = {
        "id": uuid.uuid4().hex,
        "code": _read_exec_code(args),
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_log_offset": args.include_log_offset,
    }
    exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
        "exec",
        base_url,
        payload,
        args.wait_timeout_ms,
    )
    return exit_code, stdout_text, stderr_text


def _run_wait_until_ready(args):
    selector = _resolve_selector(args)
    _validate_positive(args.ready_timeout_seconds, "ready-timeout-seconds")
    _validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    _validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    _validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=args.unity_exe_path,
            ready_timeout_seconds=args.ready_timeout_seconds,
            activity_timeout_seconds=args.activity_timeout_seconds,
            health_timeout_seconds=args.health_timeout_seconds,
        )
    else:
        session = unity_session.create_direct_session(args.base_url)
        session = unity_session.wait_until_recovered(
            session,
            args.ready_timeout_seconds,
            activity_timeout_seconds=args.activity_timeout_seconds,
            health_timeout_seconds=args.health_timeout_seconds,
        )

    payload = _success_payload("wait-until-ready", session=session, result={"status": "recovered"})
    return 0, _emit_payload(payload), ""


def _run_wait_for_log_pattern(args):
    selector = _resolve_selector(args)
    _validate_positive(args.timeout_seconds, "timeout-seconds")
    _validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    _validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    _validate_non_negative(args.start_offset, "start-offset")
    try:
        re.compile(args.pattern)
    except re.error as exc:
        raise ValueError("invalid regex: {}".format(exc))

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path)
    else:
        session = unity_session.create_direct_session(args.base_url)

    if session is None:
        payload = _expected_failure_payload(
            "wait-for-log-pattern",
            "no_observation_target",
            "no observable Unity log source is available",
        )
        return EXIT_NO_OBSERVATION_TARGET, _emit_payload(payload), ""

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
    result["diagnostics"] = {"matched_log_pattern": session.diagnostics.get("matched_log_pattern")}
    payload = _success_payload(
        "wait-for-log-pattern",
        session=session,
        result=result,
    )
    return 0, _emit_payload(payload), ""


def _run_wait_for_result_marker(args):
    selector = _resolve_selector(args)
    _validate_positive(args.timeout_seconds, "timeout-seconds")
    _validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    _validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    _validate_non_negative(args.start_offset, "start-offset")

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path)
    else:
        session = unity_session.create_direct_session(args.base_url)

    if session is None:
        payload = _expected_failure_payload(
            "wait-for-result-marker",
            "no_observation_target",
            "no observable Unity log source is available",
        )
        return EXIT_NO_OBSERVATION_TARGET, _emit_payload(payload), ""

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
            payload = _success_payload(
                "wait-for-result-marker",
                session=session,
                result={
                    "status": "result_marker_matched",
                    "marker": marker,
                    "diagnostics": {
                        "matched_log_text": session.diagnostics.get("matched_log_text"),
                        "matched_log_pattern": session.diagnostics.get("matched_log_pattern"),
                    },
                },
            )
            return 0, _emit_payload(payload), ""
        next_offset = session.diagnostics.get("matched_log_offset")
        args.start_offset = next_offset
        if next_offset is None:
            raise RuntimeError("result marker wait matched without a follow-up offset")


def _run_get_log_source(args):
    selector = _resolve_selector(args)
    if selector == "project_path":
        source = unity_session.get_log_source(project_path=args.project_path)
    else:
        source = unity_session.get_log_source(base_url=args.base_url)

    if source is None:
        payload = _expected_failure_payload(
            "get-log-source",
            "no_observation_target",
            "no observable Unity log source is available",
        )
        return EXIT_NO_OBSERVATION_TARGET, _emit_payload(payload), ""

    session, result = source
    payload = _success_payload("get-log-source", session=session, result=result)
    return 0, _emit_payload(payload), ""


def _run_ensure_stopped(args):
    selector = _resolve_selector(args)
    _validate_positive(args.timeout_seconds, "timeout-seconds")

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
        payload = _expected_failure_payload("ensure-stopped", "not_stopped", "target is not stopped", session=session)
        return EXIT_NOT_STOPPED, _emit_payload(payload), ""

    payload = _success_payload("ensure-stopped", session=session, result={"status": "stopped"})
    return 0, _emit_payload(payload), ""


def _run_command(args):
    try:
        if args.command == "exec":
            return _run_exec(args)
        if args.command == "wait-until-ready":
            return _run_wait_until_ready(args)
        if args.command == "wait-for-log-pattern":
            return _run_wait_for_log_pattern(args)
        if args.command == "wait-for-result-marker":
            return _run_wait_for_result_marker(args)
        if args.command == "get-log-source":
            return _run_get_log_source(args)
        return _run_ensure_stopped(args)
    except ValueError as exc:
        status = "address_conflict" if str(exc) == "address_conflict" else "failed"
        return _usage_error(str(exc), status=status)
    except unity_session.UnityLaunchError as exc:
        payload = _expected_failure_payload(args.command, "unity_start_failed", exc, session=exc.session)
        return EXIT_UNITY_START_FAILED, _emit_payload(payload), ""
    except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
        status = "unity_stalled" if isinstance(exc, unity_session.UnityStalledError) else "unity_not_ready"
        payload = _expected_failure_payload(args.command, status, exc, session=exc.session)
        return EXIT_UNITY_NOT_READY, _emit_payload(payload), ""
    except unity_session.UnitySessionStateError as exc:
        payload = _expected_failure_payload(args.command, exc.status, exc, session=exc.session)
        return EXIT_SESSION_STATE, _emit_payload(payload), ""
    except Exception as exc:  # noqa: BLE001 - CLI should normalize unexpected failures.
        payload = _unexpected_failure_payload(args.command, exc)
        return 1, _emit_payload(payload), ""


def _format_available_examples():
    return ", ".join(help_surface.available_example_ids())


def _handle_top_level_help(argv):
    if not argv or argv == ["--help"]:
        return 0, help_surface.render_top_level_help(), ""
    if argv[0] != "--help-example":
        return None
    if len(argv) != 2:
        return _usage_text_error(
            "usage: unity-puer-exec --help-example <example-id>\navailable examples: {}".format(_format_available_examples())
        )
    example_id = argv[1]
    if example_id not in help_surface.available_example_ids():
        return _usage_text_error(
            "unknown example id: {}\navailable examples: {}".format(example_id, _format_available_examples())
        )
    return 0, help_surface.render_workflow_example(example_id), ""


def _handle_command_help(argv):
    if not argv or argv[0] not in help_surface.COMMANDS:
        return None
    command = argv[0]
    if len(argv) == 2 and argv[1] == "--help":
        return 0, help_surface.render_command_help(command), ""
    if len(argv) == 2 and argv[1] == "--help-args":
        return 0, help_surface.render_command_args_help(command), ""
    if len(argv) == 2 and argv[1] == "--help-status":
        return 0, help_surface.render_command_status_help(command), ""
    if any(token in HELP_FLAGS for token in argv[1:]):
        return _usage_text_error(
            "usage: unity-puer-exec {} [--help | --help-args | --help-status]".format(command)
        )
    return None


def run_cli(argv):
    help_result = _handle_top_level_help(argv)
    if help_result is not None:
        return help_result
    help_result = _handle_command_help(argv)
    if help_result is not None:
        return help_result
    parser = _build_parser()
    args = parser.parse_args(argv)
    return _run_command(args)


def main():
    exit_code, stdout_text, stderr_text = run_cli(sys.argv[1:])
    if stdout_text:
        print(stdout_text)
    if stderr_text:
        print(stderr_text, file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
