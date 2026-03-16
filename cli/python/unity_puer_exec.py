#!/usr/bin/env python3
import argparse
import json
import sys
import uuid

import cli
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


def _build_parser():
    parser = argparse.ArgumentParser(prog="unity-puer-exec")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ready_parser = subparsers.add_parser("wait-until-ready")
    _add_selector_args(ready_parser)
    ready_parser.add_argument("--unity-exe-path", default=None)
    ready_parser.add_argument("--ready-timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)

    wait_log_parser = subparsers.add_parser("wait-for-log-pattern")
    _add_selector_args(wait_log_parser)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)

    get_log_source_parser = subparsers.add_parser("get-log-source")
    _add_selector_args(get_log_source_parser)

    exec_parser = subparsers.add_parser("exec")
    _add_selector_args(exec_parser)
    exec_parser.add_argument("--unity-exe-path", default=None)
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=cli.DEFAULT_WAIT_TIMEOUT_MS)
    script_source = exec_parser.add_mutually_exclusive_group(required=True)
    script_source.add_argument("--file", dest="file_path")
    script_source.add_argument("--stdin", action="store_true")
    script_source.add_argument("--code")

    get_result_parser = subparsers.add_parser("get-result")
    get_result_parser.add_argument("--base-url", required=True)
    get_result_parser.add_argument("--job-id", required=True)
    get_result_parser.add_argument("--wait-timeout-ms", type=int, default=cli.DEFAULT_WAIT_TIMEOUT_MS)

    ensure_stopped_parser = subparsers.add_parser("ensure-stopped")
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


def _usage_error(message, status="failed"):
    return 2, "", _emit_payload({"ok": False, "status": status, "error": message})


def _validate_positive(value, name):
    if value is not None and value <= 0:
        raise ValueError("{} must be positive".format(name))


def _resolve_selector(args):
    if getattr(args, "project_path", None) and getattr(args, "base_url", None):
        raise ValueError("address_conflict")
    if getattr(args, "base_url", None):
        return "base_url"
    return "project_path"


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

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=args.unity_exe_path,
        )
        base_url = session.base_url
    else:
        base_url = args.base_url

    payload = {"id": uuid.uuid4().hex, "code": _read_exec_code(args), "wait_timeout_ms": args.wait_timeout_ms}
    return cli.invoke_command("exec", base_url, payload, args.wait_timeout_ms)


def _run_get_result(args):
    _validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    payload = {"job_id": args.job_id, "wait_timeout_ms": args.wait_timeout_ms}
    return cli.invoke_command("get-result", args.base_url, payload, args.wait_timeout_ms)


def _run_wait_until_ready(args):
    selector = _resolve_selector(args)
    _validate_positive(args.ready_timeout_seconds, "ready-timeout-seconds")
    _validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    _validate_positive(args.health_timeout_seconds, "health-timeout-seconds")

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


def run_cli(argv):
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
