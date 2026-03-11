#!/usr/bin/env python3
import argparse
import json
import sys

import cli
import unity_session


EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21


def _build_parser():
    parser = argparse.ArgumentParser(prog="unity-puer-session")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure_ready_parser = subparsers.add_parser("ensure-ready")
    _add_session_args(ensure_ready_parser)
    ensure_ready_parser.add_argument(
        "--ready-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS,
    )

    wait_recovered_parser = subparsers.add_parser("wait-until-recovered")
    _add_session_args(wait_recovered_parser)
    wait_recovered_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS,
    )

    wait_log_parser = subparsers.add_parser("wait-for-log-pattern")
    _add_session_args(wait_log_parser)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS,
    )

    return parser


def _add_session_args(parser):
    parser.add_argument(
        "--project-path",
        default=None,
        help="Unity project path. Resolution order: --project-path, UNITY_PROJECT_PATH, then current working directory.",
    )
    parser.add_argument("--base-url", default=cli.DEFAULT_BASE_URL)
    parser.add_argument("--unity-exe-path", default=None)
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--activity-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    )
    parser.add_argument("--keep-unity", action="store_true")


def _emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


def _success_payload(status, session, cleanup=None):
    payload = {
        "ok": True,
        "status": "completed",
        "operation": status,
        "session": session.to_payload(),
    }
    if cleanup is not None:
        payload["cleanup"] = cleanup
    return payload


def _error_payload(status, error, session=None, cleanup=None):
    payload = {
        "ok": False,
        "status": status,
        "error": str(error),
    }
    if session is not None:
        payload["session"] = session.to_payload()
    if cleanup is not None:
        payload["cleanup"] = cleanup
    return payload


def _success_result_payload(command, session):
    if command == "ensure-ready":
        return {
            "status": "ready",
        }
    if command == "wait-until-recovered":
        return {
            "status": "recovered",
            "diagnostics": dict(session.diagnostics),
        }
    return {
        "status": "log_pattern_matched",
        "diagnostics": dict(session.diagnostics),
    }


def _ensure_session(args):
    ready_timeout_seconds = (
        args.ready_timeout_seconds if hasattr(args, "ready_timeout_seconds") else args.timeout_seconds
    )
    return unity_session.ensure_session_ready(
        project_path=args.project_path,
        base_url=args.base_url,
        unity_exe_path=args.unity_exe_path,
        ready_timeout_seconds=ready_timeout_seconds,
        activity_timeout_seconds=args.activity_timeout_seconds,
        health_timeout_seconds=args.health_timeout_seconds,
    )


def _run_command(args):
    session = None
    try:
        session = _ensure_session(args)
        if args.command == "ensure-ready":
            cleanup = unity_session.close_session(session, keep_unity=args.keep_unity)
            payload = _success_payload("ensure-ready", session, cleanup=cleanup)
            payload["result"] = _success_result_payload(args.command, session)
            return 0, _emit_payload(payload), ""

        if args.command == "wait-until-recovered":
            unity_session.wait_until_recovered(
                session,
                args.timeout_seconds,
                activity_timeout_seconds=args.activity_timeout_seconds,
                health_timeout_seconds=args.health_timeout_seconds,
            )
            cleanup = unity_session.close_session(session, keep_unity=args.keep_unity)
            payload = _success_payload("wait-until-recovered", session, cleanup=cleanup)
            payload["result"] = _success_result_payload(args.command, session)
            return 0, _emit_payload(payload), ""

        unity_session.wait_for_log_pattern(
            session,
            args.pattern,
            args.timeout_seconds,
            activity_timeout_seconds=args.activity_timeout_seconds,
            health_timeout_seconds=args.health_timeout_seconds,
        )
        cleanup = unity_session.close_session(session, keep_unity=args.keep_unity)
        payload = _success_payload("wait-for-log-pattern", session, cleanup=cleanup)
        payload["result"] = _success_result_payload(args.command, session)
        return 0, _emit_payload(payload), ""
    except unity_session.UnityLaunchError as exc:
        cleanup = None
        if exc.session is not None:
            cleanup = unity_session.close_session(exc.session, keep_unity=args.keep_unity)
        return EXIT_UNITY_START_FAILED, _emit_payload(
            _error_payload("unity_start_failed", exc, session=exc.session, cleanup=cleanup)
        ), ""
    except unity_session.UnityStalledError as exc:
        cleanup = None
        if exc.session is not None:
            cleanup = unity_session.close_session(exc.session, keep_unity=args.keep_unity)
        return EXIT_UNITY_NOT_READY, _emit_payload(
            _error_payload("unity_stalled", exc, session=exc.session, cleanup=cleanup)
        ), ""
    except unity_session.UnityNotReadyError as exc:
        cleanup = None
        if exc.session is not None:
            cleanup = unity_session.close_session(exc.session, keep_unity=args.keep_unity)
        return EXIT_UNITY_NOT_READY, _emit_payload(
            _error_payload("unity_not_ready", exc, session=exc.session, cleanup=cleanup)
        ), ""
    except Exception as exc:  # noqa: BLE001 - CLI should normalize unexpected failures.
        cleanup = unity_session.close_session(session, keep_unity=args.keep_unity) if session is not None else None
        return 1, _emit_payload(_error_payload("failed", exc, session=session, cleanup=cleanup)), ""


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
