#!/usr/bin/env python3
import argparse
import base64
import binascii
import json
import re
import sys
import uuid

import cli
import help_surface
import unity_session


EXIT_RUNNING = cli.EXIT_RUNNING
EXIT_COMPILING = cli.EXIT_COMPILING
EXIT_NOT_AVAILABLE = cli.EXIT_NOT_AVAILABLE
EXIT_MISSING = cli.EXIT_MISSING
EXIT_SESSION_STATE = 14
EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21
CONTINUATION_TOKEN_VERSION = 1
HELP_FLAGS = ("--help", "--help-args", "--help-status")


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
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)

    get_log_source_parser = subparsers.add_parser("get-log-source", add_help=False)
    _add_selector_args(get_log_source_parser)

    exec_parser = subparsers.add_parser("exec", add_help=False)
    _add_selector_args(exec_parser)
    exec_parser.add_argument("--unity-exe-path", default=None)
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=cli.DEFAULT_WAIT_TIMEOUT_MS)
    script_source = exec_parser.add_mutually_exclusive_group(required=True)
    script_source.add_argument("--file", dest="file_path")
    script_source.add_argument("--stdin", action="store_true")
    script_source.add_argument("--code")

    get_result_parser = subparsers.add_parser("get-result", add_help=False)
    get_result_parser.add_argument("--continuation-token", required=True)
    get_result_parser.add_argument("--wait-timeout-ms", type=int, default=cli.DEFAULT_WAIT_TIMEOUT_MS)

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


def _validate_project_mode_only(selector, option_name, value):
    if selector == "base_url" and value:
        raise ValueError("{} is only valid with --project-path".format(option_name))


def _resolve_selector(args):
    if getattr(args, "project_path", None) and getattr(args, "base_url", None):
        raise ValueError("address_conflict")
    if getattr(args, "base_url", None):
        return "base_url"
    return "project_path"


def _encode_continuation_token(payload):
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_continuation_token(token):
    if not token:
        raise ValueError("continuation-token is required")

    padding = "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode((token + padding).encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("malformed continuation token")

    if not isinstance(payload, dict):
        raise ValueError("malformed continuation token")

    if payload.get("v") != CONTINUATION_TOKEN_VERSION:
        raise ValueError("unsupported continuation token version")

    base_url = payload.get("base_url")
    job_id = payload.get("job_id")
    session_marker = payload.get("session_marker")
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("malformed continuation token")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("malformed continuation token")
    if not isinstance(session_marker, str) or not session_marker:
        raise ValueError("malformed continuation token")

    return {
        "v": payload["v"],
        "base_url": base_url.rstrip("/"),
        "job_id": job_id,
        "session_marker": session_marker,
    }


def _extract_session_marker(exec_payload, base_url):
    session_marker = exec_payload.get("session_marker")
    if isinstance(session_marker, str) and session_marker:
        return session_marker

    _is_ready, health_payload, _error = unity_session.inspect_direct_service(base_url)
    if health_payload is None:
        raise RuntimeError("unable to obtain session marker for continuation")

    session_marker = health_payload.get("session_marker")
    if not isinstance(session_marker, str) or not session_marker:
        raise RuntimeError("continuation target did not provide a session marker")
    return session_marker


def _add_continuation_token(stdout_text, base_url):
    payload = json.loads(stdout_text)
    if payload.get("status") != "running" or not payload.get("ok"):
        return stdout_text

    job_id = payload.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("running exec response did not include job_id")

    continuation_token = _encode_continuation_token(
        {
            "v": CONTINUATION_TOKEN_VERSION,
            "base_url": base_url.rstrip("/"),
            "job_id": job_id,
            "session_marker": _extract_session_marker(payload, base_url),
        }
    )
    payload.pop("session_marker", None)
    payload["continuation_token"] = continuation_token
    return _emit_payload(payload)


def _expected_execution_payload(status, error=None, job_id=None):
    payload = {"ok": False, "status": status}
    if job_id is not None:
        payload["job_id"] = job_id
    if error is not None:
        payload["error"] = str(error)
    return payload


def _probe_continuation_target(token_payload):
    _is_ready, health_payload, health_error = unity_session.inspect_direct_service(token_payload["base_url"])
    if health_payload is None:
        payload = _expected_execution_payload("not_available", error=health_error, job_id=token_payload["job_id"])
        return EXIT_NOT_AVAILABLE, _emit_payload(payload), ""

    session_marker = health_payload.get("session_marker")
    if not isinstance(session_marker, str) or not session_marker:
        payload = _expected_execution_payload(
            "session_missing",
            error="continuation target did not provide session continuity information",
            job_id=token_payload["job_id"],
        )
        return EXIT_SESSION_STATE, _emit_payload(payload), ""

    if session_marker != token_payload["session_marker"]:
        payload = _expected_execution_payload(
            "session_stale",
            error="continuation target session has changed since exec returned the token",
            job_id=token_payload["job_id"],
        )
        return EXIT_SESSION_STATE, _emit_payload(payload), ""

    return None


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

    payload = {"id": uuid.uuid4().hex, "code": _read_exec_code(args), "wait_timeout_ms": args.wait_timeout_ms}
    exit_code, stdout_text, stderr_text = cli.invoke_command("exec", base_url, payload, args.wait_timeout_ms)
    if stdout_text and exit_code == EXIT_RUNNING:
        stdout_text = _add_continuation_token(stdout_text, base_url)
    return exit_code, stdout_text, stderr_text


def _run_get_result(args):
    _validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    token_payload = _decode_continuation_token(args.continuation_token)
    probe_result = _probe_continuation_target(token_payload)
    if probe_result is not None:
        return probe_result

    payload = {"job_id": token_payload["job_id"], "wait_timeout_ms": args.wait_timeout_ms}
    exit_code, stdout_text, stderr_text = cli.invoke_command(
        "get-result",
        token_payload["base_url"],
        payload,
        args.wait_timeout_ms,
    )
    if exit_code == EXIT_MISSING and stdout_text:
        follow_up = _probe_continuation_target(token_payload)
        if follow_up is not None:
            return follow_up
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
    )
    payload = _success_payload(
        "wait-for-log-pattern",
        session=session,
        result={"status": "log_pattern_matched", "diagnostics": dict(session.diagnostics)},
    )
    return 0, _emit_payload(payload), ""


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
        if args.command == "get-result":
            return _run_get_result(args)
        if args.command == "wait-until-ready":
            return _run_wait_until_ready(args)
        if args.command == "wait-for-log-pattern":
            return _run_wait_for_log_pattern(args)
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
    except Exception as exc:  # noqa: BLE001 - CLI should normalize unexpected failures.
        payload = _unexpected_failure_payload(args.command, exc)
        return 1, _emit_payload(payload), ""


def _format_available_examples():
    return ", ".join(help_surface.available_example_ids())


def _handle_top_level_help(argv):
    if argv == ["--help"]:
        return 0, help_surface.render_top_level_help(), ""
    if not argv or argv[0] != "--help-example":
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
