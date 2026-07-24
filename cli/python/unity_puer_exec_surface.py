#!/usr/bin/env python3
import argparse

import cli_version
import command_registry
import direct_exec_client
import help_surface
import unity_session


HELP_FLAGS = ("--help", "--help-args", "--help-status")
VERSION_FLAG = "--version"


class ArgumentParseError(Exception):
    """Raised instead of argparse writing prose to stderr and calling sys.exit."""

    def __init__(self, message):
        super(ArgumentParseError, self).__init__(message)
        self.message = message


class _RaisingArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises ArgumentParseError on usage failures."""

    def error(self, message):
        raise ArgumentParseError(message)


def build_parser():
    parser = _RaisingArgumentParser(prog="unity-puer-exec", add_help=False)
    parser.add_argument("--suppress-guidance", action="store_true", default=False)
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=_RaisingArgumentParser)
    # Subcommand identity comes from the shared registry; argument declarations stay here.
    parsers = {
        name: subparsers.add_parser(name, add_help=False)
        for name in command_registry.COMMANDS
    }

    wait_log_parser = parsers["wait-for-log-pattern"]
    _add_selector_args(wait_log_parser)
    wait_log_parser.add_argument("--unity-log-path", default=None)
    wait_log_parser.add_argument("--pattern", required=True)
    wait_log_parser.add_argument("--start-offset", type=int, default=None)
    wait_log_parser.add_argument("--expected-session-marker", default=None)
    wait_log_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_log_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    _add_diagnostics_arg(wait_log_parser)
    _add_response_file_arg(wait_log_parser)
    extract_mode = wait_log_parser.add_mutually_exclusive_group()
    extract_mode.add_argument("--extract-group", type=int, default=None)
    extract_mode.add_argument("--extract-json-group", type=int, default=None)

    get_log_source_parser = parsers["get-log-source"]
    _add_selector_args(get_log_source_parser)
    get_log_source_parser.add_argument("--unity-log-path", default=None)
    _add_diagnostics_arg(get_log_source_parser)
    _add_response_file_arg(get_log_source_parser)

    get_blocker_state_parser = parsers["get-blocker-state"]
    get_blocker_state_parser.add_argument("--project-path", default=None)
    _add_diagnostics_arg(get_blocker_state_parser)
    _add_response_file_arg(get_blocker_state_parser)

    resolve_blocker_parser = parsers["resolve-blocker"]
    resolve_blocker_parser.add_argument("--project-path", default=None)
    resolve_blocker_parser.add_argument("--action", choices=("cancel",), required=True)
    _add_diagnostics_arg(resolve_blocker_parser)
    _add_response_file_arg(resolve_blocker_parser)

    exec_parser = parsers["exec"]
    _add_selector_args(exec_parser)
    exec_parser.add_argument("--unity-exe-path", default=None)
    exec_parser.add_argument("--unity-log-path", default=None)
    exec_parser.add_argument(
        "--unity-launch-arg",
        action="append",
        default=None,
        dest="unity_launch_args",
        help="Extra Unity argv token for a cold launch this CLI owns; repeatable.",
    )
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    exec_parser.add_argument("--request-id", default=None)
    exec_parser.add_argument("--script-args", default=None)
    exec_parser.add_argument("--include-log-offset", action="store_true")  # removed; emits usage error
    exec_parser.add_argument("--refresh-before-exec", action="store_true")
    exec_parser.add_argument("--import-base-url", default=None)
    exec_parser.add_argument("--reset-jsenv-before-exec", action="store_true")
    exec_parser.add_argument(
        "--stale-module-policy",
        choices=("auto-reset", "error"),
        default="auto-reset",
        help="How to handle changed local modules already loaded by the JsEnv.",
    )
    _add_diagnostics_arg(exec_parser)
    _add_response_file_arg(exec_parser)
    script_source = exec_parser.add_mutually_exclusive_group(required=True)
    script_source.add_argument("--file", dest="file_path")
    script_source.add_argument("--stdin", action="store_true")
    script_source.add_argument("--code")

    wait_exec_parser = parsers["wait-for-exec"]
    _add_selector_args(wait_exec_parser)
    wait_exec_parser.add_argument("--unity-exe-path", default=None)
    wait_exec_parser.add_argument("--unity-log-path", default=None)
    wait_exec_parser.add_argument(
        "--unity-launch-arg",
        action="append",
        default=None,
        dest="unity_launch_args",
        help="Extra Unity argv token for a cold launch this CLI owns; repeatable.",
    )
    wait_exec_parser.add_argument("--request-id", required=True)
    wait_exec_parser.add_argument("--wait-timeout-ms", type=int, default=direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    wait_exec_parser.add_argument("--include-log-offset", action="store_true")  # removed; emits usage error
    wait_exec_parser.add_argument("--log-start-offset", type=int, default=None)
    _add_diagnostics_arg(wait_exec_parser)
    _add_response_file_arg(wait_exec_parser)

    wait_result_parser = parsers["wait-for-result-marker"]
    _add_selector_args(wait_result_parser)
    wait_result_parser.add_argument("--unity-log-path", default=None)
    wait_result_parser.add_argument("--correlation-id", required=True)
    wait_result_parser.add_argument("--start-offset", type=int, default=None)
    wait_result_parser.add_argument("--expected-session-marker", default=None)
    wait_result_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--activity-timeout-seconds", type=float, default=unity_session.DEFAULT_ACTIVITY_TIMEOUT_SECONDS)
    wait_result_parser.add_argument("--health-timeout-seconds", type=float, default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    _add_diagnostics_arg(wait_result_parser)
    _add_response_file_arg(wait_result_parser)

    wait_compile_parser = parsers["wait-for-compile"]
    _add_selector_args(wait_compile_parser)
    wait_compile_parser.add_argument("--unity-exe-path", default=None)
    wait_compile_parser.add_argument("--unity-log-path", default=None)
    wait_compile_parser.add_argument(
        "--unity-launch-arg",
        action="append",
        default=None,
        dest="unity_launch_args",
        help="Extra Unity argv token for a cold launch this CLI owns; repeatable.",
    )
    wait_compile_parser.add_argument(
        "--appear-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS,
    )
    wait_compile_parser.add_argument(
        "--settle-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_READY_TIMEOUT_SECONDS,
    )
    wait_compile_parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS,
    )
    _add_diagnostics_arg(wait_compile_parser)
    _add_response_file_arg(wait_compile_parser)

    get_log_briefs_parser = parsers["get-log-briefs"]
    get_log_briefs_parser.add_argument("--project-path", default=None)
    get_log_briefs_parser.add_argument("--unity-log-path", default=None)
    get_log_briefs_parser.add_argument("--range", required=True, dest="range_str")
    get_log_briefs_parser.add_argument("--levels", default=None)
    get_log_briefs_parser.add_argument("--indexes", default=None, dest="indexes_str")
    get_log_briefs_parser.add_argument("--include", default=None, dest="include_str")
    get_log_briefs_parser.add_argument("--full-text", action="store_true", dest="full_text")
    _add_diagnostics_arg(get_log_briefs_parser)
    _add_response_file_arg(get_log_briefs_parser)

    ensure_stopped_parser = parsers["ensure-stopped"]
    _add_selector_args(ensure_stopped_parser)
    ensure_stopped_parser.add_argument("--timeout-seconds", type=float, default=unity_session.DEFAULT_STOP_TIMEOUT_SECONDS)
    _add_diagnostics_arg(ensure_stopped_parser)
    _add_response_file_arg(ensure_stopped_parser)
    stop_mode = ensure_stopped_parser.add_mutually_exclusive_group()
    stop_mode.add_argument("--inspect-only", action="store_true")
    stop_mode.add_argument("--immediate-kill", action="store_true")

    get_compile_errors_parser = parsers["get-compile-errors"]
    _add_selector_args(get_compile_errors_parser)
    get_compile_errors_parser.add_argument("--unity-exe-path", default=None)
    get_compile_errors_parser.add_argument("--unity-log-path", default=None)
    get_compile_errors_parser.add_argument(
        "--unity-launch-arg",
        action="append",
        default=None,
        dest="unity_launch_args",
        help="Extra Unity argv token for a cold launch this CLI owns; repeatable.",
    )
    get_compile_errors_parser.add_argument("--start", type=int, default=0)
    get_compile_errors_parser.add_argument("--count", type=int, default=3)
    _add_diagnostics_arg(get_compile_errors_parser)
    _add_response_file_arg(get_compile_errors_parser)

    get_compile_warnings_parser = parsers["get-compile-warnings"]
    _add_selector_args(get_compile_warnings_parser)
    get_compile_warnings_parser.add_argument("--unity-exe-path", default=None)
    get_compile_warnings_parser.add_argument("--unity-log-path", default=None)
    get_compile_warnings_parser.add_argument(
        "--unity-launch-arg",
        action="append",
        default=None,
        dest="unity_launch_args",
        help="Extra Unity argv token for a cold launch this CLI owns; repeatable.",
    )
    get_compile_warnings_parser.add_argument("--start", type=int, default=0)
    get_compile_warnings_parser.add_argument("--count", type=int, default=3)
    _add_diagnostics_arg(get_compile_warnings_parser)
    _add_response_file_arg(get_compile_warnings_parser)


    return parser


def resolve_command_from_argv(argv):
    """Return the first recognized command token in argv, or None."""
    known = set(command_registry.COMMANDS)
    for token in argv:
        if token in known:
            return token
    return None


def option_strings_for_command(parser, command):
    """Option strings registered on the subparser for ``command`` only."""
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        subparser = action.choices.get(command)
        if subparser is None:
            return ()
        strings = []
        for sub_action in subparser._actions:
            strings.extend(sub_action.option_strings)
        return tuple(strings)
    return ()


def handle_version(argv):
    """Answer a global `--version` before argparse rejects the missing subcommand.

    The version entry is a diagnostic like the help entries: it never contacts a
    Unity service and is never subject to the version guards, so a caller told to
    confirm its acting build by a `version_mismatch` response can always do so.
    """
    if argv != [VERSION_FLAG]:
        return None
    return 0, render_version_text(), ""


def render_version_text():
    resolved = cli_version.resolve_cli_version()
    if resolved:
        return "unity-puer-exec {}".format(resolved)
    return (
        "unity-puer-exec {}\n"
        "This build carries no stamped version and cannot be verified against "
        "the Unity Editor package it is installed with.".format(cli_version.UNKNOWN_VERSION_TEXT)
    )


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
    parser.add_argument(
        "--project-path",
        default=None,
        help="Path to the Unity project root. Optional when the exe is installed inside the target Unity project.",
    )
    parser.add_argument("--base-url", default=None)


def _add_diagnostics_arg(parser):
    parser.add_argument("--include-diagnostics", action="store_true")


def _add_response_file_arg(parser):
    parser.add_argument("--response-file", default=None, dest="response_file")


def _format_available_examples():
    return ", ".join(help_surface.available_example_ids())


def _usage_text_error(message):
    return 2, "", message
