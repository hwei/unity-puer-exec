#!/usr/bin/env python3
import argparse
import sys

import unity_puer_exec


def _build_parser():
    parser = argparse.ArgumentParser(prog="unity-puer-session")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure_ready_parser = subparsers.add_parser("ensure-ready")
    _add_session_args(ensure_ready_parser)
    ensure_ready_parser.add_argument("--ready-timeout-seconds", type=float, default=180.0)
    ensure_ready_parser.add_argument("--keep-unity", action="store_true")

    wait_recovered_parser = subparsers.add_parser("wait-until-recovered")
    _add_session_args(wait_recovered_parser)
    wait_recovered_parser.add_argument("--timeout-seconds", type=float, default=180.0)
    wait_recovered_parser.add_argument("--keep-unity", action="store_true")

    wait_log_parser = subparsers.add_parser("wait-for-log-pattern")
    _add_session_args(wait_log_parser)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=180.0)
    wait_log_parser.add_argument("--keep-unity", action="store_true")

    return parser


def _add_session_args(parser):
    parser.add_argument("--project-path", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--unity-exe-path", default=None)
    parser.add_argument("--health-timeout-seconds", type=float, default=2.0)
    parser.add_argument("--activity-timeout-seconds", type=float, default=20.0)


def run_cli(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ensure-ready":
        mapped_args = ["wait-until-ready", "--ready-timeout-seconds", str(args.ready_timeout_seconds)]
    elif args.command == "wait-until-recovered":
        mapped_args = ["wait-until-ready", "--ready-timeout-seconds", str(args.timeout_seconds)]
    else:
        mapped_args = [
            "wait-for-log-pattern",
            "--pattern",
            args.pattern,
            "--timeout-seconds",
            str(args.timeout_seconds),
        ]

    if args.project_path is not None:
        mapped_args.extend(["--project-path", args.project_path])
    if args.base_url is not None:
        mapped_args.extend(["--base-url", args.base_url])
    if args.unity_exe_path is not None:
        mapped_args.extend(["--unity-exe-path", args.unity_exe_path])
    mapped_args.extend(["--health-timeout-seconds", str(args.health_timeout_seconds)])
    mapped_args.extend(["--activity-timeout-seconds", str(args.activity_timeout_seconds)])
    return unity_puer_exec.run_cli(mapped_args)


def main():
    exit_code, stdout_text, stderr_text = run_cli(sys.argv[1:])
    if stdout_text:
        print(stdout_text)
    if stderr_text:
        print(stderr_text, file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
