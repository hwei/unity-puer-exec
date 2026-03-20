#!/usr/bin/env python3
import argparse

import direct_exec_client
import help_surface
import unity_session


HELP_FLAGS = ("--help", "--help-args", "--help-status")


def build_parser():
    parser = argparse.ArgumentParser(prog="unity-puer-exec", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ready_parser = subparsers.add_parser("wait-until-ready", add_help=False)
    _add_selector_args(ready_parser)
    ready_parser.add_argument("--unity-exe-path", default=None)
    ready_parser.add_argument("--unity-log-path", default=None)
    ready_parser.add_argument("--ready-timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    ready_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    _add_diagnostics_arg(ready_parser)

    wait_log_parser = subparsers.add_parser("wait-for-log-pattern", add_help=False)
    _add_selector_args(wait_log_parser)
    wait_log_parser.add_argument("--unity-log-path", default=None)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument("--start-offset", type=int, default=None)
    wait_log_parser.add_argument("--expected-session-marker", default=None)
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    _add_diagnostics_arg(wait_log_parser)
    extract_mode = wait_log_parser.add_mutually_exclusive_group()
    extract_mode.add_argument("--extract-group", type=int, default=None)
    extract_mode.add_argument("--extract-json-group", type=int, default=None)

    get_log_source_parser = subparsers.add_parser("get-log-source", add_help=False)
    _add_selector_args(get_log_source_parser)
    get_log_source_parser.add_argument("--unity-log-path", default=None)
    _add_diagnostics_arg(get_log_source_parser)

    get_blocker_state_parser = subparsers.add_parser("get-blocker-state", add_help=False)
    get_blocker_state_parser.add_argument("--project-path", default=None)
    _add_diagnostics_arg(get_blocker_state_parser)

    exec_parser = subparsers.add_parser("exec", add_help=False)
    _add_selector_args(exec_parser)
    exec_parser.add_argument("--unity-exe-path", default=None)
    exec_parser.add_argument("--unity-log-path", default=None)
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    exec_parser.add_argument("--request-id", default=None)
    exec_parser.add_argument("--include-log-offset", action="store_true")
    _add_diagnostics_arg(exec_parser)
    script_source = exec_parser.add_mutually_exclusive_group(required=True)
    script_source.add_argument("--file", dest="file_path")
    script_source.add_argument("--stdin", action="store_true")
    script_source.add_argument("--code")

    wait_exec_parser = subparsers.add_parser("wait-for-exec", add_help=False)
    _add_selector_args(wait_exec_parser)
    wait_exec_parser.add_argument("--unity-exe-path", default=None)
    wait_exec_parser.add_argument("--unity-log-path", default=None)
    wait_exec_parser.add_argument("--request-id", required=True)
    wait_exec_parser.add_argument("--wait-timeout-ms", type=int, default=direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    wait_exec_parser.add_argument("--include-log-offset", action="store_true")
    _add_diagnostics_arg(wait_exec_parser)

    wait_result_parser = subparsers.add_parser("wait-for-result-marker", add_help=False)
    _add_selector_args(wait_result_parser)
    wait_result_parser.add_argument("--unity-log-path", default=None)
    wait_result_parser.add_argument("--correlation-id", required=True)
    wait_result_parser.add_argument("--start-offset", type=int, default=None)
    wait_result_parser.add_argument("--expected-session-marker", default=None)
    wait_result_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    _add_diagnostics_arg(wait_result_parser)

    ensure_stopped_parser = subparsers.add_parser("ensure-stopped", add_help=False)
    _add_selector_args(ensure_stopped_parser)
    ensure_stopped_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_STOP_TIMEOUT_SECONDS)
    _add_diagnostics_arg(ensure_stopped_parser)
    stop_mode = ensure_stopped_parser.add_mutually_exclusive_group()
    stop_mode.add_argument("--inspect-only", action="store_true")
    stop_mode.add_argument("--immediate-kill", action="store_true")

    return parser


def handle_top_level_help(argv):
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


def handle_command_help(argv):
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


def _add_selector_args(parser):
    parser.add_argument("--project-path", default=None)
    parser.add_argument("--base-url", default=None)


def _add_diagnostics_arg(parser):
    parser.add_argument("--include-diagnostics", action="store_true")


def _format_available_examples():
    return ", ".join(help_surface.available_example_ids())


def _usage_text_error(message):
    return 2, "", message
