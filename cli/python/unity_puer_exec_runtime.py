#!/usr/bin/env python3
import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid

import cli_version
import command_registry
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
EXIT_MODULE_CACHE_STALE = direct_exec_client.EXIT_MODULE_CACHE_STALE
EXIT_UNITY_COMPILE_ERROR = direct_exec_client.EXIT_UNITY_COMPILE_ERROR
EXIT_VERSION_MISMATCH = direct_exec_client.EXIT_VERSION_MISMATCH
EXIT_SESSION_STATE = 14
EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
# A terminal outcome for an automatic refresh the CLI itself could not settle
# (make-base-url-exec-refresh-recoverable). Deliberately not `missing` (13):
# `missing` means the addressed service holds no recoverable record for the
# request_id, while here the CLI holds the request it never let through -- the
# script has not run, and re-submitting it runs the script for the first time.
EXIT_REFRESH_UNSETTLED = 25
# Terminal outcome detail codes for EXIT_REFRESH_UNSETTLED, named so a caller can
# branch without parsing prose.
REFRESH_UNSETTLED_SETTLE_TIMEOUT = "refresh_settle_timeout"
REFRESH_UNSETTLED_REFRESH_PERSISTED = "refresh_persisted"
REFRESH_UNSETTLED_COMPILE_IN_PROGRESS = "compile_in_progress"
# A running Editor that never activated a control service. Distinct from a launch
# failure (20) and a readiness failure (21) so a caller can tell that retrying
# cannot help and an activation decision is what is missing.
EXIT_EDITOR_NOT_UNDER_CLI_CONTROL = 17
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21
STALE_MODULE_POLICY_AUTO_RESET = "auto-reset"
STALE_MODULE_POLICY_ERROR = "error"
RESULT_MARKER_PREFIX = "[UnityPuerExecResult]"
RESULT_MARKER_PATTERN = r"(?m)^\[UnityPuerExecResult\] (.+)$"
PHASE_REFRESHING = "refreshing"
PHASE_COMPILING = "compiling"
PHASE_EXECUTING = "executing"
PHASE_PLAY_MODE = "play_mode"
HEALTH_STATUS_READY = "ready"
HEALTH_STATUS_COMPILING = "compiling"
# Edge-aware wait-for-compile outcomes (see openspec compile-wait spec).
COMPILE_OUTCOME_READY = "ready"
COMPILE_OUTCOME_NONE = "no_compile_observed"
COMPILE_OUTCOME_BLOCKED = "compile_blocked"
COMPILE_OUTCOME_TIMEOUT = "settle_timeout"
# A compile inferred from an advanced caller-supplied compile generation. It is a
# distinct outcome from `ready` because no `compiling` status was ever observed; the
# generation advance is the edge (see openspec compile-wait spec).
COMPILE_OUTCOME_GENERATION = "generation_advance"
# Name of the edge reported when an advanced baseline settles an inferred compile.
COMPILE_EDGE_GENERATION_ADVANCE = "generation_advance"

# Play-mode compile block (see surface-play-mode-compile-block). Unity defers
# compilation until play mode exits, so a pending change cannot compile while the
# Editor is playing. The condition is named rather than reported as a plain success.
PLAY_MODE_REASON = "play_mode"
WARNING_COMPILE_BLOCKED_BY_PLAY_MODE = "compile_blocked_by_play_mode"
WARNING_DETAIL_COMPILE_BLOCKED_BY_PLAY_MODE = (
    "The script ran, but a compile-triggering change is still pending and the Editor "
    "is in play mode. Unity defers compilation until play mode exits, so the result "
    "does not include the pending change."
)
SCRIPT_CHANGES_WHILE_PLAYING_UNKNOWN = "unknown"
# ScriptUpdater consent dialog recovery (see api-updater-recovery spec). This is a
# sidecar field on whatever status the command would otherwise return, never a
# replacement for `status: "warning"` (the async-exec-result contract).
API_UPDATER_WARNING = "api_updater_declined"
API_UPDATER_WARNING_DETAIL = (
    "Unity offered to rewrite project source files for changed APIs; the CLI "
    "declined (clicked No) so no sources were modified. Existing compile errors "
    "or (UnityUpgradable) messages may remain; use get-compile-errors / "
    "get-compile-warnings to inspect them."
)


def emit_payload(payload):
    return json.dumps(payload, ensure_ascii=True)


class _ApiUpdaterRecovery:
    """Per-invocation count of ScriptUpdater consent dialogs declined.

    A command owns one of these for its whole lifecycle and records declines from
    every wait it performs, so the warning can be attached to whatever terminal
    status the command produces.
    """

    def __init__(self):
        self.declines = 0

    def record(self, count):
        if count:
            self.declines += count


def _attach_api_updater_warning(payload):
    if isinstance(payload, dict):
        payload["warning"] = API_UPDATER_WARNING
        payload["warning_detail"] = API_UPDATER_WARNING_DETAIL
    return payload


def _apply_api_updater_warning(result, recovery):
    """Attach the api_updater_declined sidecar field to a command's JSON response."""
    if recovery is None or not recovery.declines:
        return result
    exit_code, stdout_text, stderr_text = result
    if stdout_text:
        body = json.loads(stdout_text)
        return exit_code, emit_payload(_attach_api_updater_warning(body)), stderr_text
    if stderr_text:
        body = json.loads(stderr_text)
        return exit_code, stdout_text, emit_payload(_attach_api_updater_warning(body))
    return result


def _dismiss_api_updater_for_pid(unity_pid):
    if not unity_pid:
        return 0
    try:
        result = unity_modal_blockers.dismiss_api_updater_dialog(unity_pid)
    except Exception:  # noqa: BLE001 - dialog recovery never fails the command.
        return 0
    return result.get("dismissed", 0)


def usage_error(message, status="failed", command=None, args=None):
    payload = {"ok": False, "status": status, "error": message}
    if command is not None and args is not None:
        _attach_guidance(payload, command, status, args)
    if status == "address_conflict":
        return 2, emit_payload(payload), ""
    return 2, "", emit_payload(payload)


# Near-match cutoff for rejected options against the invoked command's own flags.
# 0.6 keeps the reported `--timeout-ms` → `--wait-timeout-ms` case while omitting weak guesses.
_OPTION_NEAR_MATCH_CUTOFF = 0.6
_UNRECOGNIZED_ARGUMENTS_RE = re.compile(r"unrecognized arguments:\s*(.+)$")


def _extract_unrecognized_options(message):
    match = _UNRECOGNIZED_ARGUMENTS_RE.search(message or "")
    if match is None:
        return ()
    return tuple(token for token in match.group(1).split() if token.startswith("-"))


def _suggest_option(parser, surface, command, rejected_option):
    candidates = surface.option_strings_for_command(parser, command)
    if not candidates:
        return None
    matches = difflib.get_close_matches(
        rejected_option,
        candidates,
        n=1,
        cutoff=_OPTION_NEAR_MATCH_CUTOFF,
    )
    return matches[0] if matches else None


def _parse_failure_args(argv, command):
    return argparse.Namespace(
        command=command,
        suppress_guidance="--suppress-guidance" in list(argv or ()),
    )


def handle_parse_failure(argv, parser, surface, message):
    """Build the structured invalid_arguments envelope for a parse-layer rejection."""
    command = surface.resolve_command_from_argv(argv)
    payload = {
        "ok": False,
        "status": "invalid_arguments",
        "error": message,
    }
    if command is not None:
        payload["command"] = command
        for rejected in _extract_unrecognized_options(message):
            suggestion = _suggest_option(parser, surface, command, rejected)
            if suggestion is not None:
                payload["suggested_option"] = suggestion
                break
        args = _parse_failure_args(argv, command)
        _attach_guidance(payload, command, "invalid_arguments", args)
    else:
        if "--suppress-guidance" not in list(argv or ()):
            payload["situation"] = (
                "The invocation was rejected before any command was identified. "
                "Consult top-level help for the available commands."
            )
            payload["next_steps"] = [
                {
                    "command": "--help",
                    "when": "you want the top-level command list and global options",
                    "argv": ["unity-puer-exec", "--help"],
                }
            ]
    return 2, "", emit_payload(payload)


_RESPONSE_FILE_ROUTING_FIELDS = (
    "ok",
    "status",
    "operation",
    "request_id",
    "phase",
    "session_marker",
    "cli_version",
)


def _inject_cli_version(text):
    """Stamp the acting CLI build onto a machine-readable response.

    Applied once at the end of `run_cli`, so every response family carries it --
    including the normalized exec/wait bodies and usage errors that never pass
    through the payload builders -- and before the response-file projection, so
    the compact reference inherits it through the routing fields.
    """
    if not text:
        return text
    try:
        body = json.loads(text)
    except ValueError:
        return text
    if not isinstance(body, dict) or "cli_version" in body:
        return text
    body["cli_version"] = cli_version.version_text(cli_version.resolve_cli_version())
    return emit_payload(body)


def _atomic_write_bytes(path, data):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".unity-puer-exec-response-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _project_response_file(response_file_path, exit_code, stdout_text, stderr_text):
    """Persist the exact unprojected JSON response to `response_file_path` and emit a
    compact verifiable reference on the same stream in its place (see design.md #2/#3).
    """
    if not response_file_path:
        return exit_code, stdout_text, stderr_text
    if stdout_text:
        stream, target_text = "stdout", stdout_text
    elif stderr_text:
        stream, target_text = "stderr", stderr_text
    else:
        return exit_code, stdout_text, stderr_text

    try:
        body = json.loads(target_text)
    except ValueError:
        return exit_code, stdout_text, stderr_text

    data = target_text.encode("utf-8")
    abs_path = os.path.abspath(response_file_path)

    try:
        _atomic_write_bytes(abs_path, data)
    except OSError as exc:
        if isinstance(body, dict):
            body["response_file_error"] = str(exc)
            new_text = emit_payload(body)
        else:
            new_text = target_text
        if stream == "stdout":
            return exit_code, new_text, stderr_text
        return exit_code, stdout_text, new_text

    reference = {}
    if isinstance(body, dict):
        for key in _RESPONSE_FILE_ROUTING_FIELDS:
            if key in body:
                reference[key] = body[key]
    reference["response_file"] = {
        "path": abs_path,
        "encoding": "utf-8",
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    ref_text = emit_payload(reference)
    if stream == "stdout":
        return exit_code, ref_text, stderr_text
    return exit_code, stdout_text, ref_text


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


# brief_sequence sentinel + operator hint emitted when the Unity host reports that
# stack-trace logging is disabled. Without stack traces, runtime log briefs cannot
# reliably delimit entries (see openspec/specs/log-brief), so a real brief_sequence
# would be misleading. The C# server reports the condition via stack_trace_logging.degraded.
_BRIEF_SEQUENCE_STACKTRACE_OFF = "!stacktrace-off"
_BRIEF_HINT_STACKTRACE_OFF = (
    "Enable ScriptOnly/Full stack trace logging (Console > Stack Trace Logging or "
    "Application.SetStackTraceLogType) for meaningful log briefs."
)


def _stack_trace_logging_degraded(container):
    stack_trace_logging = container.get("stack_trace_logging")
    return isinstance(stack_trace_logging, dict) and bool(stack_trace_logging.get("degraded"))


def _detect_offset_invalidation(log_path, caller_start_offset):
    """Report a caller-supplied start offset that lies past the end of the log.

    Reading still rescans from the beginning -- dropping the read would be worse --
    but a byte range recorded before a rotation or truncation no longer denotes the
    content the caller meant, and absorbing that silently turns into an unexplained
    wait timeout. An observation that supplies no offset passes None here and cannot
    trip the signal.
    """
    if caller_start_offset is None or log_path is None:
        return None
    observed_end = unity_session_logs.read_editor_log_size(log_path)
    if observed_end is None or caller_start_offset <= observed_end:
        return None
    return {
        "log_path": str(log_path),
        "supplied_start": caller_start_offset,
        "observed_end": observed_end,
        "reason": "log_rotated_or_truncated",
        "detail": (
            "the supplied start offset {} is past the end ({}) of the observed log {}; "
            "the log was rotated or truncated, so earlier byte offsets no longer denote "
            "the intended content and the scan restarted from the beginning"
        ).format(caller_start_offset, observed_end, log_path),
    }


def _apply_log_range_and_brief_sequence(container, log_path, log_start, log_end, offsets_invalidated=None):
    container["log_range"] = {"start": log_start, "end": log_end}
    if offsets_invalidated is not None:
        container["log_offsets_invalidated"] = offsets_invalidated
    if _stack_trace_logging_degraded(container):
        container["brief_sequence"] = _BRIEF_SEQUENCE_STACKTRACE_OFF
        container["brief_hint"] = _BRIEF_HINT_STACKTRACE_OFF
        return
    briefs = unity_log_brief.parse_log_briefs(log_path, log_start, log_end)
    container["brief_sequence"] = unity_log_brief.build_brief_sequence(briefs)


def _inject_log_range_into_stdout(stdout_text, log_path, log_start, log_end, offsets_invalidated=None):
    if not stdout_text:
        return stdout_text
    body = json.loads(stdout_text)
    _apply_log_range_and_brief_sequence(body, log_path, log_start, log_end, offsets_invalidated=offsets_invalidated)
    return emit_payload(body)


def _inject_log_range_into_payload(payload, log_path, log_start, log_end, offsets_invalidated=None):
    _apply_log_range_and_brief_sequence(payload, log_path, log_start, log_end, offsets_invalidated=offsets_invalidated)


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


def version_mismatch_payload(operation, detail):
    return {
        "ok": False,
        "status": cli_version.STATUS_VERSION_MISMATCH,
        "operation": operation,
        "error": cli_version.mismatch_message(detail),
        "version_mismatch": dict(detail),
    }


def _version_mismatch_result(args, detail):
    payload = version_mismatch_payload(args.command, detail)
    _attach_guidance(payload, args.command, cli_version.STATUS_VERSION_MISMATCH, args)
    return EXIT_VERSION_MISMATCH, emit_payload(payload), ""


def _local_version_guards(args):
    """Guards that need nothing but the local installation, run before any work."""
    argv0 = getattr(args, "argv0", None)
    resolved = cli_version.resolve_cli_version()
    detail = cli_version.check_cli_version_known(resolved, argv0=argv0)
    if detail is not None:
        return detail
    return cli_version.check_package_layout(resolved, argv0=argv0)


def _base_url_bridge_guard(args):
    """Bridge guard for the selector that never otherwise probes health.

    A transport failure is not a guard failure: the endpoint reported nothing to
    compare, and the command's own not_available handling is the right answer.
    """
    try:
        if resolve_selector(args) != "base_url":
            return None
    except ValueError:
        # A malformed selector combination is a usage error; let the command say so
        # rather than spending a probe on an invocation that cannot run.
        return None
    base_url = args.base_url
    payload, error = unity_session.probe_health_payload(base_url)
    if payload is None or error is not None:
        return None
    return cli_version.check_bridge(cli_version.resolve_cli_version(), base_url, payload)


def run_command(args):
    detail = _local_version_guards(args)
    if detail is None:
        detail = _base_url_bridge_guard(args)
    if detail is not None:
        return _version_mismatch_result(args, detail)
    try:
        if args.command == "exec":
            return run_exec(args)
        if args.command == "wait-for-exec":
            return run_wait_for_exec(args)
        if args.command == "wait-for-log-pattern":
            return run_wait_for_log_pattern(args)
        if args.command == "wait-for-result-marker":
            return run_wait_for_result_marker(args)
        if args.command == "wait-for-compile":
            return run_wait_for_compile(args)
        if args.command == "get-log-source":
            return run_get_log_source(args)
        if args.command == "get-blocker-state":
            return run_get_blocker_state(args)
        if args.command == "resolve-blocker":
            return run_resolve_blocker(args)
        if args.command == "get-log-briefs":
            return run_get_log_briefs(args)
        if args.command == "get-compile-errors":
            return run_get_compile_errors(args)
        if args.command == "get-compile-warnings":
            return run_get_compile_warnings(args)
        if command_registry.canonical_command(args.command) == "ensure-closed":
            return run_ensure_closed(args)
        if args.command == "play":
            return run_play(args)
        if args.command == "pause":
            return run_pause(args)
        if args.command == "stop":
            return run_stop(args)
        return run_ensure_closed(args)
    except unity_session.UnityVersionMismatchError as exc:
        return _version_mismatch_result(args, exc.detail)
    except ValueError as exc:
        if len(exc.args) >= 2 and isinstance(exc.args[1], str):
            return usage_error(str(exc.args[0]), status=exc.args[1], command=args.command, args=args)
        status = "address_conflict" if str(exc) == "address_conflict" else "failed"
        return usage_error(str(exc), status=status, command=args.command, args=args)
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
    except unity_session.UnityEditorNotUnderControlError as exc:
        # Its own exit code, distinct from launch (20) and readiness (21) failures,
        # because the remedy is an activation decision rather than a retry.
        payload = expected_failure_payload(
            args.command,
            exc.status,
            exc,
            session=exc.session,
            include_diagnostics=getattr(args, "include_diagnostics", False),
        )
        payload["ways_forward"] = list(exc.guidance)
        _attach_guidance(payload, args.command, exc.status, args)
        return EXIT_EDITOR_NOT_UNDER_CLI_CONTROL, emit_payload(payload), ""
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


def run_cli(argv, surface, argv0=None):
    filtered_argv = [a for a in argv if a != "--suppress-guidance"]
    version_result = surface.handle_version(filtered_argv)
    if version_result is not None:
        return version_result
    help_result = surface.handle_top_level_help(filtered_argv)
    if help_result is not None:
        return help_result
    help_result = surface.handle_command_help(filtered_argv)
    if help_result is not None:
        return help_result
    parser = surface.build_parser()
    try:
        args = parser.parse_args(argv)
    except surface.ArgumentParseError as exc:
        exit_code, stdout_text, stderr_text = handle_parse_failure(argv, parser, surface, exc.message)
        stdout_text = _inject_cli_version(stdout_text)
        stderr_text = _inject_cli_version(stderr_text)
        return exit_code, stdout_text, stderr_text
    args.argv0 = argv0
    exit_code, stdout_text, stderr_text = run_command(args)
    stdout_text = _inject_cli_version(stdout_text)
    stderr_text = _inject_cli_version(stderr_text)
    return _project_response_file(getattr(args, "response_file", None), exit_code, stdout_text, stderr_text)


def read_exec_code(args):
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    return args.code


def _project_path_arg(args):
    return str(unity_session.resolve_project_path(getattr(args, "project_path", None), argv0=getattr(args, "argv0", None)))


def _build_guidance_context(args, request_id=None):
    context = {}
    project_path = getattr(args, "project_path", None)
    if project_path:
        context["project_path"] = str(unity_session.resolve_project_path(project_path))
    if request_id:
        context["request_id"] = request_id
    if getattr(args, "wait_timeout_ms", None) is not None:
        context["wait_timeout_ms"] = args.wait_timeout_ms
    # `--base-url` is not a documented forwardable arg, but the base-url
    # continuation candidates are built from it (see help_surface._select_argv),
    # so it has to reach the guidance context.
    base_url = getattr(args, "base_url", None)
    if base_url:
        context["base_url"] = str(base_url)
    if getattr(args, "unity_exe_path", None):
        context["unity_exe_path"] = args.unity_exe_path
    if getattr(args, "unity_log_path", None):
        context["unity_log_path"] = args.unity_log_path
    if getattr(args, "file_path", None):
        context["file_path"] = str(args.file_path)
    if getattr(args, "include_diagnostics", False):
        context["include_diagnostics"] = True
    return context


_BARE_PUER_REFERENCE_ERROR_RE = re.compile(r"^ReferenceError: \$(typeof|ref) is not defined$")
_SYNTAX_ERROR_RE = re.compile(r"(?i)^\s*SyntaxError\b")
# Signature of a shell-expanded `$token` that left a member access immediately followed by a call.
_SHELL_EXPANSION_SIGNATURE_RE = re.compile(r"\.\s*\(")


def _maybe_hint_puer_prefix(payload, command, args=None):
    if command not in ("exec", "wait-for-exec") or payload.get("status") != "failed":
        return
    error = payload.get("error")
    if not isinstance(error, str):
        return
    match = _BARE_PUER_REFERENCE_ERROR_RE.match(error.strip())
    if match is not None:
        name = match.group(1)
        hint = "This looks like a missing `puer.` prefix: did you mean `puer.${}` instead of bare `${}`?".format(name, name)
        situation = payload.get("situation")
        payload["situation"] = "{} {}".format(situation, hint) if situation else hint
        return
    # Shell-expansion form: only for inline `--code`, never `--file` / `--stdin`.
    if args is None or not getattr(args, "code", None):
        return
    if getattr(args, "file_path", None) or getattr(args, "stdin", False):
        return
    if _SYNTAX_ERROR_RE.match(error.strip()) is None:
        return
    if _SHELL_EXPANSION_SIGNATURE_RE.search(args.code) is None:
        return
    hint = (
        "This looks like a shell expanded a `$` token inside double-quoted `--code` "
        "(for example turning `puer.$typeof(...)` into `puer.(...)`). "
        "Use single quotes around `--code`, or pass the script through `--file`."
    )
    situation = payload.get("situation")
    payload["situation"] = "{} {}".format(situation, hint) if situation else hint


def _attach_guidance(payload, command, status, args, request_id=None):
    if getattr(args, "suppress_guidance", False):
        return
    context = _build_guidance_context(args, request_id=request_id)
    # Enrich context from CLI-owned envelope fields on the response payload.
    # log_range is injected before guidance is attached, so the payload
    # already carries CLI-owned byte offsets for the observation window.
    log_range = payload.get("log_range") if isinstance(payload, dict) else None
    if isinstance(log_range, dict):
        _log_start = log_range.get("start")
        _log_end = log_range.get("end")
        if _log_start is not None and _log_end is not None:
            context["log_range_span"] = "{}-{}".format(_log_start, _log_end)
    # `refresh_block` is a CLI-composed envelope object (never a script-authored
    # result field), so its presence is a CLI-owned guidance selector: it adds the
    # play-mode exit guidance to whatever the warning/status already selected.
    compile_blocked = isinstance(payload.get("compile_blocked"), dict)
    next_steps = help_surface.build_next_steps(
        command, status, context, warning=payload.get("warning"), compile_blocked=compile_blocked,
        replayable_record=_has_replayable_record(payload),
    )
    if next_steps:
        payload["next_steps"] = next_steps
    detail = payload.get("version_mismatch")
    guard = detail.get("guard") if isinstance(detail, dict) else None
    situation = help_surface.build_situation(
        command, status, guard=guard, warning=payload.get("warning"), compile_blocked=compile_blocked
    )
    if situation:
        payload["situation"] = situation
    _maybe_hint_puer_prefix(payload, command, args=args)


def _inject_guidance_into_stdout(stdout_text, command, args, request_id=None):
    if not stdout_text or getattr(args, "suppress_guidance", False):
        return stdout_text
    body = json.loads(stdout_text)
    rid = request_id or body.get("request_id")
    _attach_guidance(body, command, body.get("status"), args, request_id=rid)
    return emit_payload(body)


def _inject_guidance_into_response(stdout_text, stderr_text, command, args, request_id=None):
    """Like _inject_guidance_into_stdout, but also covers the stderr-carried case.

    exec/wait-for-exec route some failed responses (e.g. a thrown script error) to
    stderr rather than stdout; guidance built from GUIDANCE_MATRIX -- including the
    puer. prefix hint -- must reach those responses too.
    """
    if stdout_text:
        return _inject_guidance_into_stdout(stdout_text, command, args, request_id=request_id), stderr_text
    if not stderr_text or getattr(args, "suppress_guidance", False):
        return stdout_text, stderr_text
    body = json.loads(stderr_text)
    rid = request_id or body.get("request_id")
    _attach_guidance(body, command, body.get("status"), args, request_id=rid)
    return stdout_text, emit_payload(body)


def _pending_exec_payload(
    request_id,
    code,
    script_args,
    script_args_json,
    phase=None,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args": script_args,
        "script_args_json": script_args_json,
        "reset_jsenv_before_exec": bool(reset_jsenv_before_exec),
        "stale_module_policy": stale_module_policy or STALE_MODULE_POLICY_AUTO_RESET,
    }
    if source_path:
        payload["source_path"] = source_path
    if import_base_url:
        payload["import_base_url"] = import_base_url
    if phase:
        payload["phase"] = phase
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
    phase=None,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
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
            phase=phase,
            source_path=source_path,
            import_base_url=import_base_url,
            reset_jsenv_before_exec=reset_jsenv_before_exec,
            stale_module_policy=stale_module_policy,
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


def _has_replayable_record(payload):
    """Whether the addressed service holds a record `wait-for-exec --request-id` can replay.

    Presence follows the record, not the CLI's ability to fill an argv template.
    The CLI-composed envelope denies the record explicitly
    (`record_replayable: false`) for a request the service never accepted -- the
    `refresh_unsettled` case. Every other response that carries the candidate
    reached the server's accept path, so a record exists in either selector. The
    selector shape is deliberately not consulted: inferring the answer from it is
    what made an accepted base-url request look like an unreplayable one.
    """
    return payload.get("record_replayable") is not False


def _emit_refresh_unsettled_payload(
    operation, session, request_id, args, refresh=None, phase=None,
    reason=REFRESH_UNSETTLED_SETTLE_TIMEOUT, base_url=None, wait_timeout_ms=None,
):
    """Terminal response for an automatic refresh the CLI could not settle.

    Non-terminal while the refresh is still in flight, but the settle has reached
    the compile-scale budget, so this invocation will not converge on the script
    result. Reporting `running` here kept the response's own `next_steps`
    promising a `wait-for-exec --request-id` continuation that answers `missing`,
    because the server had not accepted the job at the refreshing phase and
    base-url mode keeps no client-side record.
    """
    payload = {
        "ok": False,
        "status": "refresh_unsettled",
        "operation": operation,
        "request_id": request_id,
        "error": reason,
        "reason": reason,
        "situation": (
            "This CLI triggered an automatic refresh whose compile cycle did not settle "
            "within its own compile-scale budget, so the script has not run yet and this "
            "invocation stopped waiting. The request was never accepted by the service and "
            "this CLI keeps no replayable record for it, so `wait-for-exec --request-id` "
            "cannot continue it. Re-submit the same `exec`; because the script never ran, "
            "a re-submit runs it for the first time."
        ),
        "record_replayable": False,
        "resubmit_safe": True,
        "recoverable": True,
        "phase": phase or PHASE_REFRESHING,
    }
    if refresh is not None:
        payload["refresh"] = refresh
    if base_url is None:
        base_url = getattr(args, "base_url", None)
    if base_url:
        payload["base_url"] = base_url
    if wait_timeout_ms is None:
        wait_timeout_ms = getattr(args, "wait_timeout_ms", None)
    if wait_timeout_ms is not None:
        payload["wait_timeout_ms"] = wait_timeout_ms
    if session is not None:
        payload["session"] = session.to_payload()
    _attach_guidance(payload, operation, "refresh_unsettled", args, request_id=request_id)
    return attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)


def _emit_running_payload(operation, session, request_id, args, phase=None, refresh=None, record_replayable=None):
    payload = {
        "ok": True,
        "status": "running",
        "operation": operation,
        "request_id": request_id,
    }
    if phase:
        payload["phase"] = phase
    if refresh is not None:
        payload["refresh"] = refresh
    if record_replayable is not None:
        payload["record_replayable"] = record_replayable
    if session is not None:
        payload["session"] = session.to_payload()
    _attach_guidance(payload, operation, "running", args, request_id=request_id)
    return attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)


def _build_exec_payload(
    request_id,
    code,
    script_args_json,
    args,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = {
        "request_id": request_id,
        "code": code,
        "script_args_json": script_args_json,
        "wait_timeout_ms": args.wait_timeout_ms,
        "include_diagnostics": args.include_diagnostics,
        "stale_module_policy": stale_module_policy or STALE_MODULE_POLICY_AUTO_RESET,
    }
    if source_path:
        payload["source_path"] = source_path
    if import_base_url:
        payload["import_base_url"] = import_base_url
    if reset_jsenv_before_exec:
        payload["reset_jsenv_before_exec"] = True
    return payload


def _invoke_exec(
    base_url,
    request_id,
    code,
    script_args_json,
    args,
    source_path=None,
    import_base_url=None,
    reset_jsenv_before_exec=False,
    stale_module_policy=STALE_MODULE_POLICY_AUTO_RESET,
):
    payload = _build_exec_payload(
        request_id,
        code,
        script_args_json,
        args,
        source_path=source_path,
        import_base_url=import_base_url,
        reset_jsenv_before_exec=reset_jsenv_before_exec,
        stale_module_policy=stale_module_policy,
    )
    return direct_exec_client.invoke_command(
        "exec",
        base_url,
        payload,
        args.wait_timeout_ms,
    )


def _post_refresh_ready_timeout_seconds(args):
    """Budget for settling the compile cycle an automatic refresh started.

    Deliberately not `--wait-timeout-ms`. That option bounds one HTTP wait for an
    already-accepted job, while this bounds a compile plus the domain reload it ends
    with -- tens of seconds, not one. Deriving one from the other is what let a
    base-url `exec` bail out of its own settle, return the refreshing phase without
    resubmitting, and leave the caller a request the server had never accepted (see
    diagnose-exec-missing-after-auto-refresh). It is the same budget
    `wait-for-compile --settle-timeout-seconds` gives the identical cycle.
    """
    return max(float(unity_session.DEFAULT_READY_TIMEOUT_SECONDS), 0.001)


def _ensure_project_session_ready_after_refresh(args):
    return unity_session.ensure_session_ready(
        project_path=args.project_path,
        unity_exe_path=args.unity_exe_path,
        unity_log_path=args.unity_log_path,
        unity_launch_args=getattr(args, "unity_launch_args", None),
        ready_timeout_seconds=_post_refresh_ready_timeout_seconds(args),
        argv0=getattr(args, "argv0", None),
    )


def _probe_compile_health(base_url, health_timeout_seconds):
    return unity_session._probe_health(base_url, health_timeout_seconds)


def _script_changes_while_playing_from_health(payload):
    """Read the Editor's play-time compile preference from a health payload.

    The server reports one of the three preference labels, or ``unknown`` when the
    key is absent or unrecognized. A missing or blank field is treated the same as
    ``unknown`` rather than guessing.
    """
    refresh = payload.get("refresh") if isinstance(payload, dict) else None
    if isinstance(refresh, dict):
        value = refresh.get("script_changes_while_playing")
        if isinstance(value, str) and value:
            return value
    return SCRIPT_CHANGES_WHILE_PLAYING_UNKNOWN


def _read_play_mode_preference(base_url, health_timeout_seconds):
    """Best-effort health read of the play-time compile preference.

    Only called when the Editor is already known to be blocking a compile in play
    mode, so the extra probe never runs on the ordinary exec path. A transport
    failure degrades to ``unknown`` rather than failing the exec response.
    """
    try:
        payload, _error = _probe_compile_health(base_url, health_timeout_seconds)
    except Exception:  # noqa: BLE001 - preference is advisory only.
        return SCRIPT_CHANGES_WHILE_PLAYING_UNKNOWN
    return _script_changes_while_playing_from_health(payload)


def _is_play_mode_compile_block(payload):
    """True when health shows a pending change suppressed by play mode.

    Requires a positive pending state. ``unknown`` is not treated as pending, so an
    invalidated signal never fabricates a compile block.
    """
    if not isinstance(payload, dict):
        return False
    refresh = payload.get("refresh")
    if not isinstance(refresh, dict):
        return False
    return (
        refresh.get("pending") == "pending"
        and bool(refresh.get("suppressed"))
        and refresh.get("suppressed_reason") == PLAY_MODE_REASON
    )


def _compile_generation_from_health(payload):
    """Read the Editor's monotonic compile generation from a health payload.

    Returns an int, or None when the field is absent or not an integer -- an older
    Editor that predates the signal, or a non-ready payload. Never coerces a
    non-integer: a missing signal must not fabricate an inferred compile.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get("compile_generation")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _record_observed_status(observed, status):
    if status is not None and (not observed or observed[-1] != status):
        observed.append(status)


def wait_for_compile_cycle(
    base_url,
    appear_timeout_seconds,
    settle_timeout_seconds,
    health_timeout_seconds,
    appear_poll_interval=unity_session.COMPILE_APPEAR_POLL_INTERVAL_SECONDS,
    settle_poll_interval=unity_session.POLL_INTERVAL_SECONDS,
    probe_health_fn=None,
    time_ref=None,
    unity_pid=None,
    dismiss_fn=None,
    compile_generation_baseline=None,
):
    """Edge-aware wait for a single Unity compilation cycle over `/health`.

    Phase 1 (appear): within ``appear_timeout_seconds`` wait for the editor to
    report ``compiling`` (or detect a compile already in progress). An initial
    ``ready`` is never treated as terminal, defeating the async-refresh race. If a
    previously-ready endpoint drops (transport error after a healthy probe), that is
    treated as a domain-reload edge.

    When ``compile_generation_baseline`` is supplied and the health payload reports a
    strictly greater ``compile_generation``, the compile is settled immediately as
    ``generation_advance`` even if the endpoint was already ``ready``. This covers a
    deferred play-exit compile, whose forced synchronous recompile runs after the
    listener has stopped, so ``compiling`` is never observable.

    Phase 2 (settle): wait up to ``settle_timeout_seconds`` for the editor to return
    to ``ready``. Transient transport errors during this phase are tolerated as
    still-in-progress until the ready/timeout boundary.

    While waiting, a visible ScriptUpdater consent dialog for the Editor process is
    auto-declined (No) and never treated as a settled compile. The pid comes from
    the caller's session or a ``unity_pid`` on a compiling health payload.

    Returns a dict with ``outcome`` in {``ready``, ``no_compile_observed``,
    ``compile_blocked``, ``generation_advance``, ``settle_timeout``}, the
    ``observed_health`` status sequence, and ``api_updater_declines``.
    """
    time_ref = time if time_ref is None else time_ref
    probe_health_fn = probe_health_fn or _probe_compile_health
    dismiss_fn = _dismiss_api_updater_for_pid if dismiss_fn is None else dismiss_fn
    observed = []
    seen_healthy = False
    edge_observed = False
    declines = 0

    def maybe_dismiss(payload):
        nonlocal declines
        pid = unity_pid
        if pid is None and isinstance(payload, dict):
            reported = payload.get("unity_pid")
            if isinstance(reported, int) and reported > 0:
                pid = reported
        if pid:
            declines += dismiss_fn(pid)

    appear_deadline = time_ref.time() + appear_timeout_seconds
    while True:
        payload, _error = probe_health_fn(base_url, health_timeout_seconds)
        status = payload.get("status") if isinstance(payload, dict) else None
        _record_observed_status(observed, status)
        # A caller-supplied baseline that has advanced is a direct observation that a
        # compilation completed, so it settles even when the endpoint was already
        # ready. Its outcome is distinct from `ready`: no `compiling` was seen, and the
        # edge was inferred from the baseline rather than observed as a status.
        generation = _compile_generation_from_health(payload)
        if (
            compile_generation_baseline is not None
            and generation is not None
            and generation > compile_generation_baseline
        ):
            return {
                "outcome": COMPILE_OUTCOME_GENERATION,
                "observed_health": observed,
                "api_updater_declines": declines,
                "edge": COMPILE_EDGE_GENERATION_ADVANCE,
                "compile_generation": generation,
                "compile_generation_baseline": compile_generation_baseline,
            }
        # A pending change that cannot compile because the Editor is in play mode is
        # named immediately, before the appear window settles. An already-running
        # compile (status compiling) has no refresh block and still settles normally.
        if _is_play_mode_compile_block(payload):
            return {
                "outcome": COMPILE_OUTCOME_BLOCKED,
                "observed_health": observed,
                "api_updater_declines": declines,
                "reason": PLAY_MODE_REASON,
                "script_changes_while_playing": _script_changes_while_playing_from_health(payload),
            }
        # Poll for a blocking consent dialog for the whole appear window, not only
        # once `compiling` is observed.
        maybe_dismiss(payload)
        if status == HEALTH_STATUS_COMPILING:
            edge_observed = True
            break
        if status == HEALTH_STATUS_READY:
            seen_healthy = True
        elif payload is None and seen_healthy:
            # Endpoint dropped after being healthy: a refresh-triggered domain reload
            # tears the control endpoint down, so treat this as the compile edge.
            edge_observed = True
            break
        if time_ref.time() >= appear_deadline:
            break
        time_ref.sleep(appear_poll_interval)

    if not edge_observed:
        return {
            "outcome": COMPILE_OUTCOME_NONE,
            "observed_health": observed,
            "api_updater_declines": declines,
        }

    settle_deadline = time_ref.time() + settle_timeout_seconds
    while True:
        payload, _error = probe_health_fn(base_url, health_timeout_seconds)
        status = payload.get("status") if isinstance(payload, dict) else None
        _record_observed_status(observed, status)
        if status == HEALTH_STATUS_READY:
            return {
                "outcome": COMPILE_OUTCOME_READY,
                "observed_health": observed,
                "api_updater_declines": declines,
            }
        maybe_dismiss(payload)
        if time_ref.time() >= settle_deadline:
            return {
                "outcome": COMPILE_OUTCOME_TIMEOUT,
                "observed_health": observed,
                "api_updater_declines": declines,
            }
        time_ref.sleep(settle_poll_interval)


def _settle_base_url_after_refresh(base_url, args, recovery=None):
    """Base-url analog of `_ensure_project_session_ready_after_refresh`.

    Re-probes the same caller-supplied endpoint, reusing the compile-wait primitive,
    so an automatic refresh settles on the compile cycle before running the script.
    """
    settle_timeout_seconds = _post_refresh_ready_timeout_seconds(args)
    cycle = wait_for_compile_cycle(
        base_url,
        getattr(args, "appear_timeout_seconds", unity_session.DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS),
        settle_timeout_seconds,
        getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS),
    )
    if recovery is not None:
        recovery.record(cycle.get("api_updater_declines", 0))
    return cycle


def _is_refresh_pending_response(exit_code, stdout_text):
    """True when an exec response reports an automatic refresh phase.

    Refresh is non-terminal: the CLI settles the compile cycle it started and
    re-submits the same request_id, so a caller never receives a refresh
    confirmation in place of the script result.
    """
    if not stdout_text:
        return False
    try:
        body = json.loads(stdout_text)
    except (TypeError, ValueError):
        return False
    if not isinstance(body, dict):
        return False
    if body.get("status") == "running" and body.get("phase") == PHASE_REFRESHING:
        return True
    refresh = body.get("refresh")
    return isinstance(refresh, dict) and refresh.get("triggered") is True


def _extract_refresh_block(stdout_text):
    if not stdout_text:
        return None
    try:
        body = json.loads(stdout_text)
    except (TypeError, ValueError):
        return None
    block = body.get("refresh") if isinstance(body, dict) else None
    return block if isinstance(block, dict) else None


def _inject_refresh_block_into_stdout(stdout_text, refresh_block):
    if not stdout_text or refresh_block is None:
        return stdout_text
    try:
        body = json.loads(stdout_text)
    except (TypeError, ValueError):
        return stdout_text
    if not isinstance(body, dict):
        return stdout_text
    body["refresh"] = refresh_block
    return emit_payload(body)


def _response_body_and_stream(stdout_text, stderr_text):
    """Return the JSON response body and which stream carried it.

    exec routes successes to stdout and some failures (a thrown script) to stderr,
    so the play-mode rewrite has to consider both. stdout is preferred when both
    parse, matching the CLI's normal stream selection.
    """
    for stream, text in (("stdout", stdout_text), ("stderr", stderr_text)):
        if not text:
            continue
        try:
            body = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(body, dict):
            return body, stream
    return None, None


def _build_compile_blocked(pending_paths, script_changes_while_playing):
    return {
        "reason": PLAY_MODE_REASON,
        "pending_paths": list(pending_paths),
        "script_changes_while_playing": (
            script_changes_while_playing or SCRIPT_CHANGES_WHILE_PLAYING_UNKNOWN
        ),
    }


def _apply_play_mode_compile_block(stdout_text, stderr_text, base_url, args):
    """Disclose a compile-triggering change that play mode prevents from compiling.

    The refresh block already reports ``skipped_reason: play_mode`` and the pending
    paths, but a ``completed`` exec then reads as an ordinary success. When a change
    is actually pending, attach a ``compile_blocked`` object and turn a plain
    ``completed`` into a warning. A failure status or an existing warning (for
    example ``async_result_not_supported``) keeps its status and code; the object is
    the reliable signal in every case.
    """
    body, source = _response_body_and_stream(stdout_text, stderr_text)
    if body is None:
        return stdout_text, stderr_text
    if body.get("status") == "running":
        # A non-terminal response has no terminal script result to annotate; the
        # block is disclosed only once the request reaches a terminal state.
        return stdout_text, stderr_text
    refresh = body.get("refresh")
    if not isinstance(refresh, dict) or refresh.get("skipped_reason") != PLAY_MODE_REASON:
        return stdout_text, stderr_text
    pending_paths = refresh.get("paths_changed")
    if not isinstance(pending_paths, list) or not pending_paths:
        return stdout_text, stderr_text

    preference = _read_play_mode_preference(
        base_url,
        getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS),
    )
    body["compile_blocked"] = _build_compile_blocked(pending_paths, preference)
    if body.get("status") == "completed":
        body["status"] = "warning"
        body["warning"] = WARNING_COMPILE_BLOCKED_BY_PLAY_MODE
        body["warning_detail"] = WARNING_DETAIL_COMPILE_BLOCKED_BY_PLAY_MODE
    serialized = emit_payload(body)
    if source == "stdout":
        return serialized, stderr_text
    return stdout_text, serialized


def _settle_after_automatic_refresh(args, selector, session, base_url, recovery):
    """Settle the compile cycle an automatic refresh started.

    Returns ``(session, base_url)`` once the cycle settled, or ``None`` while it is
    still running, so the caller reports a non-terminal refreshing phase.
    """
    try:
        if selector == "project_path":
            session = _ensure_project_session_ready_after_refresh(args)
            recovery.record(getattr(session, "api_updater_declines", 0))
            session.api_updater_declines = 0
            return session, session.base_url
        cycle = _settle_base_url_after_refresh(base_url, args, recovery=recovery)
        if cycle.get("outcome") == COMPILE_OUTCOME_TIMEOUT:
            return None
        return session, base_url
    except (unity_session.UnityStalledError, unity_session.UnityNotReadyError):
        return None


def _invoke_reset_jsenv(base_url, args):
    return direct_exec_client.invoke_command(
        "reset-jsenv",
        base_url,
        {},
        args.wait_timeout_ms,
    )


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


def _resolve_source_path(args):
    if getattr(args, "file_path", None):
        return os.path.abspath(args.file_path)
    return None


def _exec_import_base_url(args):
    value = getattr(args, "import_base_url", None)
    return value if value else None


def _exec_reset_flag(args):
    return bool(getattr(args, "reset_jsenv_before_exec", False))


def _exec_stale_module_policy(args):
    return getattr(args, "stale_module_policy", None) or STALE_MODULE_POLICY_AUTO_RESET


def run_exec(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_exec_impl(args, recovery)
    return _apply_api_updater_warning(result, recovery)


def _run_exec_impl(args, recovery):
    if getattr(args, "include_log_offset", False):
        return usage_error(
            "--include-log-offset has been removed; use log_range.start from exec response",
            command="exec",
            args=args,
        )
    if getattr(args, "refresh_before_exec", False):
        return usage_error(
            "--refresh-before-exec has been removed; refresh is now automatic for code changes. "
            "Saving the change is itself the trigger, so re-run exec instead.",
            status="removed_refresh_flag",
            command="exec",
            args=args,
        )
    request_id = args.request_id or uuid.uuid4().hex
    code = read_exec_code(args)
    script_args, script_args_json = _canonicalize_script_args(getattr(args, "script_args", None))
    source_path = _resolve_source_path(args)
    import_base_url = _exec_import_base_url(args)
    reset_jsenv_before_exec = _exec_reset_flag(args)
    stale_module_policy = _exec_stale_module_policy(args)
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        _sweep_pending_exec(args)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
                unity_launch_args=getattr(args, "unity_launch_args", None),
                argv0=getattr(args, "argv0", None),
            )
        except (unity_session.UnityStalledError, unity_session.UnityNotReadyError) as exc:
            _write_pending_exec(
                args,
                request_id,
                code,
                script_args,
                script_args_json,
                source_path=source_path,
                import_base_url=import_base_url,
                reset_jsenv_before_exec=reset_jsenv_before_exec,
                stale_module_policy=stale_module_policy,
            )
            payload = _emit_running_payload("exec", exc.session, request_id, args)
            _rp1_log_path = _resolve_log_path(args, exc.session)
            _rp1_log_end = _capture_log_offset(_rp1_log_path)
            _inject_log_range_into_payload(payload, _rp1_log_path, _rp1_log_end, _rp1_log_end)
            return EXIT_RUNNING, emit_payload(payload), ""
        recovery.record(getattr(session, "api_updater_declines", 0))
        session.api_updater_declines = 0
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    log_path = _resolve_log_path(args, session)
    log_start = _capture_log_offset(log_path)

    if selector == "project_path":
        _write_pending_exec(
            args,
            request_id,
            code,
            script_args,
            script_args_json,
            source_path=source_path,
            import_base_url=import_base_url,
            reset_jsenv_before_exec=reset_jsenv_before_exec,
            stale_module_policy=stale_module_policy,
        )

    refresh_block = None
    refresh_attempts = 0
    while True:
        exit_code, stdout_text, stderr_text = _invoke_exec(
            base_url,
            request_id,
            code,
            script_args_json,
            args,
            source_path=source_path,
            import_base_url=import_base_url,
            reset_jsenv_before_exec=reset_jsenv_before_exec,
            stale_module_policy=stale_module_policy,
        )
        exit_code, stdout_text, stderr_text = _normalize_exec_blocker_result(
            exit_code,
            stdout_text,
            stderr_text,
            session if selector == "project_path" else None,
            log_path=log_path if selector == "project_path" else None,
        )
        if not _is_refresh_pending_response(exit_code, stdout_text):
            break
        # The server detected a compile-triggering change and refreshed. Refresh is a
        # non-terminal phase of this accepted request: settle the compile cycle, then
        # re-submit the same request_id so the terminal response carries the script
        # result rather than a refresh confirmation.
        refresh_block = _extract_refresh_block(stdout_text) or refresh_block
        if selector == "project_path":
            _refresh_pending_exec(args, request_id, _read_pending_exec(args, request_id), PHASE_REFRESHING)
        settled = _settle_after_automatic_refresh(args, selector, session, base_url, recovery)
        if settled is None:
            # The refresh is still in flight, so the phase stays non-terminal --
            # but it is still terminal for THIS invocation: the compile-scale settle
            # budget is spent and the CLI keeps no record it can replay, so an
            # accepted-looking `running` here would only promise a continuation that
            # answers `missing`. Report the exhaustion with a resubmit path instead.
            if selector == "base_url":
                payload = _emit_refresh_unsettled_payload(
                    "exec", None, request_id, args, refresh=refresh_block,
                )
                _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
                return EXIT_REFRESH_UNSETTLED, emit_payload(payload), ""
            payload = _emit_running_payload(
                "exec", session, request_id, args, phase=PHASE_REFRESHING, refresh=refresh_block
            )
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
            return EXIT_RUNNING, emit_payload(payload), ""
        if refresh_attempts >= 1:
            # The single permitted resubmit is answered `refreshing` again, so the
            # request is still unaccepted. Base-url mode has no pending artifact to
            # replay, so this is the second branch whose record exists nowhere.
            if selector == "base_url":
                payload = _emit_refresh_unsettled_payload(
                    "exec", None, request_id, args, refresh=refresh_block,
                    reason=REFRESH_UNSETTLED_REFRESH_PERSISTED,
                )
                _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
                return EXIT_REFRESH_UNSETTLED, emit_payload(payload), ""
            payload = _emit_running_payload(
                "exec", session, request_id, args, phase=PHASE_REFRESHING, refresh=refresh_block
            )
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
            return EXIT_RUNNING, emit_payload(payload), ""
        session, base_url = settled
        if selector == "project_path":
            _set_pending_phase(args, request_id, _read_pending_exec(args, request_id), PHASE_EXECUTING)
        refresh_attempts += 1

    if selector == "base_url" and _is_compiling_response(exit_code, stdout_text):
        # The post-settle resubmit was answered `compiling`: the server rejected it
        # before `TryAcceptExecRequest`, so the script has not run and no record
        # exists. Project-path mode normalizes this to `running` because its pending
        # artifact gives `wait-for-exec --request-id` something to replay; base-url
        # mode has none, so report the terminal outcome rather than an accepted-looking
        # non-terminal state.
        payload = _emit_refresh_unsettled_payload(
            "exec", None, request_id, args, refresh=refresh_block,
            phase=PHASE_COMPILING, reason=REFRESH_UNSETTLED_COMPILE_IN_PROGRESS,
        )
        _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path))
        return EXIT_REFRESH_UNSETTLED, emit_payload(payload), ""

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
    stdout_text = _inject_refresh_block_into_stdout(stdout_text, refresh_block)
    stdout_text = _inject_log_range_into_stdout(stdout_text, log_path, log_start, _capture_log_offset(log_path))
    stdout_text, stderr_text = _apply_play_mode_compile_block(stdout_text, stderr_text, base_url, args)
    stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "exec", args, request_id=request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_for_exec(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_wait_for_exec_impl(args, recovery)
    return _apply_api_updater_warning(result, recovery)


def _run_wait_for_exec_impl(args, recovery):
    if getattr(args, "include_log_offset", False):
        return usage_error(
            "--include-log-offset has been removed; use log_range.start from exec response",
            command="wait-for-exec",
            args=args,
        )
    selector = resolve_selector(args)
    validate_positive(args.wait_timeout_ms, "wait-timeout-ms")
    validate_project_mode_only(selector, "unity-exe-path", args.unity_exe_path)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    _wfe_log_path_early = getattr(args, "unity_log_path", None) or str(unity_session_logs.default_editor_log_path())
    _wfe_log_start = args.log_start_offset if args.log_start_offset is not None else _capture_log_offset(_wfe_log_path_early)
    _wfe_offsets_invalidated = _detect_offset_invalidation(_wfe_log_path_early, args.log_start_offset)

    if selector == "project_path":
        _sweep_pending_exec(args)
        pending = _read_pending_exec(args, args.request_id)
        try:
            session = unity_session.ensure_session_ready(
                project_path=args.project_path,
                unity_exe_path=args.unity_exe_path,
                unity_log_path=args.unity_log_path,
                unity_launch_args=getattr(args, "unity_launch_args", None),
                argv0=getattr(args, "argv0", None),
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
                _inject_log_range_into_payload(payload, _wfe_rp1_log_path, _wfe_log_start, _capture_log_offset(_wfe_rp1_log_path), offsets_invalidated=_wfe_offsets_invalidated)
                return EXIT_RUNNING, emit_payload(payload), ""
            raise
        recovery.record(getattr(session, "api_updater_declines", 0))
        session.api_updater_declines = 0
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url
        pending = None
    if pending is not None:
        if pending.get("phase") == PHASE_REFRESHING:
            # The recorded exec triggered an automatic refresh. Settle the compile
            # cycle, then replay the user exec under the same request_id.
            settled = _settle_after_automatic_refresh(args, selector, session, base_url, recovery)
            if settled is None:
                payload = _emit_running_payload("wait-for-exec", session, args.request_id, args, phase=PHASE_REFRESHING)
                _inject_log_range_into_payload(payload, _wfe_log_path_early, _wfe_log_start, _capture_log_offset(_wfe_log_path_early), offsets_invalidated=_wfe_offsets_invalidated)
                return EXIT_RUNNING, emit_payload(payload), ""
            session, base_url = settled
            pending = _refresh_pending_exec(args, args.request_id, pending, PHASE_EXECUTING)
        exit_code, stdout_text, stderr_text = _invoke_exec(
            base_url,
            args.request_id,
            pending["code"],
            pending["script_args_json"],
            args,
            source_path=pending.get("source_path"),
            import_base_url=pending.get("import_base_url"),
            reset_jsenv_before_exec=bool(pending.get("reset_jsenv_before_exec")),
            stale_module_policy=pending.get("stale_module_policy", STALE_MODULE_POLICY_AUTO_RESET),
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
        log_path=_wfe_log_path_early if selector == "project_path" else None,
    )
    if selector == "project_path" and pending is not None and _is_refresh_pending_response(exit_code, stdout_text):
        _refresh_pending_exec(args, args.request_id, _read_pending_exec(args, args.request_id), PHASE_REFRESHING)
        payload = _emit_running_payload("wait-for-exec", session, args.request_id, args, phase=PHASE_REFRESHING)
        _inject_log_range_into_payload(payload, _wfe_log_path_early, _wfe_log_start, _capture_log_offset(_wfe_log_path_early), offsets_invalidated=_wfe_offsets_invalidated)
        return EXIT_RUNNING, emit_payload(payload), ""
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
    stdout_text = _inject_log_range_into_stdout(stdout_text, _wfe_final_log_path, _wfe_log_start, _capture_log_offset(_wfe_final_log_path), offsets_invalidated=_wfe_offsets_invalidated)
    # The replayed exec response carries the same refresh block, so the terminal
    # response discloses a play-mode compile block exactly as `exec` does. Only the
    # terminal path is rewritten; the non-terminal returns above are left alone.
    stdout_text, stderr_text = _apply_play_mode_compile_block(stdout_text, stderr_text, base_url, args)
    stdout_text, stderr_text = _inject_guidance_into_response(stdout_text, stderr_text, "wait-for-exec", args, request_id=args.request_id)
    return exit_code, stdout_text, stderr_text


def run_wait_for_compile(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_wait_for_compile_impl(args, recovery)
    return _apply_api_updater_warning(result, recovery)


def _run_wait_for_compile_impl(args, recovery):
    selector = resolve_selector(args)
    validate_positive(args.appear_timeout_seconds, "appear-timeout-seconds")
    validate_positive(args.settle_timeout_seconds, "settle-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")

    validate_project_mode_only(selector, "unity-exe-path", getattr(args, "unity_exe_path", None))
    validate_project_mode_only(selector, "unity-log-path", getattr(args, "unity_log_path", None))
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=getattr(args, "unity_exe_path", None),
            unity_log_path=getattr(args, "unity_log_path", None),
            unity_launch_args=getattr(args, "unity_launch_args", None),
            argv0=getattr(args, "argv0", None),
        )
        recovery.record(getattr(session, "api_updater_declines", 0))
        session.api_updater_declines = 0
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    cycle = wait_for_compile_cycle(
        base_url,
        args.appear_timeout_seconds,
        args.settle_timeout_seconds,
        args.health_timeout_seconds,
        unity_pid=session.unity_pid if session is not None else None,
        compile_generation_baseline=getattr(args, "compile_generation_baseline", None),
    )
    recovery.record(cycle.get("api_updater_declines", 0))
    outcome = cycle["outcome"]
    diagnostics = {"observed_health": cycle["observed_health"]}

    if outcome == COMPILE_OUTCOME_BLOCKED:
        # The pending change cannot compile until play mode exits. Name the block
        # instead of reporting no_compile_observed, and return without waiting out
        # the appear window.
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={
                "status": "compile_blocked",
                "compile_observed": False,
                "reason": cycle.get("reason", PLAY_MODE_REASON),
                "script_changes_while_playing": cycle.get(
                    "script_changes_while_playing", SCRIPT_CHANGES_WHILE_PLAYING_UNKNOWN
                ),
            },
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "compile_blocked", args)
        return 0, emit_payload(payload), ""

    if outcome == COMPILE_OUTCOME_GENERATION:
        # An inferred cross-reload compile: the caller's baseline advanced, even though
        # no `compiling` status was observable. Name the edge so the caller can see why
        # the command settled without ever seeing a compile window.
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={
                "status": "compile_settled",
                "compile_observed": True,
                "edge": COMPILE_EDGE_GENERATION_ADVANCE,
                "compile_generation": cycle.get("compile_generation"),
                "compile_generation_baseline": cycle.get("compile_generation_baseline"),
            },
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "completed", args)
        return 0, emit_payload(payload), ""

    if outcome == COMPILE_OUTCOME_READY:
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={"status": "compile_settled", "compile_observed": True},
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "completed", args)
        return 0, emit_payload(payload), ""

    if outcome == COMPILE_OUTCOME_NONE:
        payload = success_payload(
            "wait-for-compile",
            session=session,
            result={"status": "no_compile_observed", "compile_observed": False},
            include_diagnostics=args.include_diagnostics,
            diagnostics=diagnostics,
        )
        _attach_guidance(payload, "wait-for-compile", "no_compile_observed", args)
        return 0, emit_payload(payload), ""

    # settle_timeout: an observed compile did not return to ready in time. Surface a
    # non-terminal running/timeout result rather than falsely reporting completion.
    payload = {
        "ok": True,
        "status": "running",
        "operation": "wait-for-compile",
        "phase": PHASE_COMPILING,
    }
    if session is not None:
        payload["session"] = session.to_payload()
    payload = attach_diagnostics(
        payload,
        include_diagnostics=args.include_diagnostics,
        session=session,
        diagnostics=diagnostics,
    )
    _attach_guidance(payload, "wait-for-compile", "running", args)
    return EXIT_RUNNING, emit_payload(payload), ""


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
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
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
    offsets_invalidated = _detect_offset_invalidation(log_path, args.start_offset)

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
        _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
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
    _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
    _attach_guidance(payload, "wait-for-log-pattern", "completed", args)
    return 0, emit_payload(payload), ""


def run_wait_for_result_marker(args):
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")
    validate_positive(args.activity_timeout_seconds, "activity-timeout-seconds")
    validate_positive(args.health_timeout_seconds, "health-timeout-seconds")
    validate_non_negative(args.start_offset, "start-offset")
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)

    if selector == "project_path":
        session = unity_session.create_observation_session(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
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
    offsets_invalidated = _detect_offset_invalidation(log_path, args.start_offset)

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
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
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
            _inject_log_range_into_payload(payload, log_path, log_start, _capture_log_offset(log_path), offsets_invalidated=offsets_invalidated)
            return 0, emit_payload(payload), ""
        next_offset = session.diagnostics.get("matched_log_offset")
        args.start_offset = next_offset
        if next_offset is None:
            raise RuntimeError("result marker wait matched without a follow-up offset")


def run_get_log_source(args):
    selector = resolve_selector(args)
    validate_project_mode_only(selector, "unity-log-path", args.unity_log_path)
    if selector == "project_path":
        source = unity_session.get_log_source(project_path=args.project_path, unity_log_path=args.unity_log_path, argv0=getattr(args, "argv0", None))
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
    session = unity_session.get_blocker_state(project_path=args.project_path, argv0=getattr(args, "argv0", None))
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

    session = unity_session.get_blocker_state(project_path=args.project_path, argv0=getattr(args, "argv0", None))
    result = unity_modal_blockers.resolve_modal_blocker(
        session.unity_pid,
        action=args.action,
        hwnd=getattr(args, "hwnd", None),
        button=getattr(args, "button", None),
    )
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

    indexes_str = getattr(args, "indexes_str", None)
    include_str = getattr(args, "include_str", None)
    _INDEXES_FORMAT_ERROR = (
        "--indexes must be comma-separated 1-based brief indices, e.g. `--indexes 3,5`, "
        "corresponding to `brief_sequence` positions"
    )

    def _parse_indexes(raw):
        try:
            return [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise ValueError(_INDEXES_FORMAT_ERROR)

    include_indices = None
    if indexes_str and include_str:
        parsed_indexes = _parse_indexes(indexes_str)
        parsed_include = _parse_indexes(include_str)
        if parsed_indexes != parsed_include:
            raise ValueError(
                "--indexes and --include were both supplied with different values; "
                "supply only one, or make them match",
                "conflicting_indexes_include",
            )
        include_indices = parsed_indexes
    elif indexes_str or include_str:
        include_indices = _parse_indexes(indexes_str or include_str)

    full_text = getattr(args, "full_text", False)
    if full_text and not include_indices:
        raise ValueError(
            "--full-text requires --indexes (or its --include alias) with one or more explicit 1-based brief indices",
            "full_text_requires_include",
        )

    log_path = getattr(args, "unity_log_path", None)
    if log_path is None and getattr(args, "project_path", None):
        source = unity_session.get_log_source(project_path=args.project_path, argv0=getattr(args, "argv0", None))
        if source is not None:
            log_path = source[0].effective_log_path
    if log_path is None:
        log_path = str(unity_session_logs.default_editor_log_path())

    briefs = unity_log_brief.parse_log_briefs(log_path, range_start, range_end)
    filtered = unity_log_brief.filter_briefs(briefs, levels=levels, include_indices=include_indices)
    if full_text:
        selected_indices = set(include_indices or ())
        for brief in filtered:
            if brief.get("index") in selected_indices:
                brief["full_text"] = unity_log_brief.full_text_for_brief(log_path, brief)

    payload = success_payload(
        "get-log-briefs",
        result=filtered,
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(payload, "get-log-briefs", "completed", args)
    return 0, emit_payload(payload), ""


def _run_get_compile_messages(args, command_name):
    """Shared implementation for get-compile-errors / get-compile-warnings."""
    selector = resolve_selector(args)
    validate_non_negative(args.start, "start")
    if args.count < 1 or args.count > 100:
        raise ValueError("count must be between 1 and 100")
    validate_project_mode_only(selector, "unity-exe-path", getattr(args, "unity_exe_path", None))
    validate_project_mode_only(selector, "unity-log-path", getattr(args, "unity_log_path", None))
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=getattr(args, "unity_exe_path", None),
            unity_log_path=getattr(args, "unity_log_path", None),
            unity_launch_args=getattr(args, "unity_launch_args", None),
            argv0=getattr(args, "argv0", None),
        )
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    payload = {"start": args.start, "count": args.count}
    exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
        command_name,
        base_url,
        payload,
        5000,
    )
    if exit_code != 0:
        stdout_text, stderr_text = _inject_guidance_into_response(
            stdout_text, stderr_text, command_name, args
        )
        return exit_code, stdout_text, stderr_text
    body = json.loads(stdout_text)
    result = {
        "total": body.get("total", 0),
        "start": body.get("start", 0),
        "returned": body.get("returned", 0),
        "messages": body.get("messages", []),
        "session_marker": body.get("session_marker", ""),
    }
    response = success_payload(
        command_name,
        session=session,
        result=result,
        include_diagnostics=args.include_diagnostics,
    )
    _attach_guidance(response, command_name, "completed", args)
    return 0, emit_payload(response), ""


def run_get_compile_errors(args):
    return _run_get_compile_messages(args, "get-compile-errors")


def run_get_compile_warnings(args):
    return _run_get_compile_messages(args, "get-compile-warnings")


# --- Play-mode commands (play / pause / stop) -------------------------------

PLAY_STATE_EDIT = "edit"
PLAY_STATE_ENTERING = "entering"
PLAY_STATE_PLAYING = "playing"
PLAY_STATE_PAUSED = "paused"
PLAY_STATE_EXITING = "exiting"

PLAY_ACTION_TARGET = {
    "play": PLAY_STATE_PLAYING,
    "pause": PLAY_STATE_PAUSED,
    "stop": PLAY_STATE_EDIT,
}


def _health_play_state(payload):
    value = payload.get("play_state") if isinstance(payload, dict) else None
    return value if isinstance(value, str) and value else None


def _parse_response_body(stdout_text, stderr_text):
    for text in (stdout_text, stderr_text):
        if not text:
            continue
        try:
            body = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(body, dict):
            return body
    return None


def _play_probe_endpoint(selector, args, base_url, health_timeout_seconds):
    """Probe the target and return ``(play_state, payload, base_url)``.

    ``play_state`` is ``None`` when no ready target answered. In project mode the
    endpoint is re-resolved on every probe, because a play-mode domain reload can
    drop the listener and rebind it on a different port.
    """
    if selector == "project_path":
        candidate, payload, _error, _other = unity_session.discover_project_endpoint(
            args.project_path, health_timeout_seconds=health_timeout_seconds
        )
        if candidate is None:
            return None, None, base_url
        return _health_play_state(payload), payload, candidate
    payload, _error = unity_session.probe_health_payload(base_url, health_timeout_seconds)
    if not isinstance(payload, dict) or not (payload.get("ok") and payload.get("status") == HEALTH_STATUS_READY):
        return None, payload, base_url
    return _health_play_state(payload), payload, base_url


def _is_play_mode_transport_drop(body):
    """True when a play-mode body names a reload edge rather than a command result.

    ``empty_response`` and ``not_available`` are transport conditions (the endpoint
    dropped mid-reload); an absent route (``http_status == 404``) is also
    ``not_available`` but must stay terminal so the caller can report a version
    mismatch. A missing body is treated as a drop defensively.
    """
    if body is None:
        return True
    if body.get("http_status") == 404:
        return False
    return body.get("status") in (direct_exec_client.STATUS_EMPTY_RESPONSE, "not_available")


def _post_play_mode(selector, args, session, base_url, action, force_run_in_background):
    """Post the play-mode action, re-resolving a dropped endpoint within a bound.

    A transport drop (an empty/unreachable body) is a domain-reload edge: re-resolve
    the endpoint and retry until the command's ``timeout_seconds`` budget elapses.
    Every server-answered body is returned immediately. When the budget elapses the
    last observed structured state is returned so the envelope can report its formal
    exit code instead of collapsing it into a generic failure.
    """
    payload = {"action": action, "force_run_in_background": bool(force_run_in_background)}
    wait_ms = getattr(args, "wait_timeout_ms", direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    health_timeout = getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    deadline = time.monotonic() + max(float(getattr(args, "timeout_seconds", 0.0)), 0.001)
    last_exit_code = EXIT_NOT_AVAILABLE
    last_body = None
    while True:
        exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
            "play-mode", base_url, payload, wait_ms
        )
        body = _parse_response_body(stdout_text, stderr_text)
        last_exit_code = exit_code
        if body is not None:
            last_body = body
        if body is not None and not _is_play_mode_transport_drop(body):
            return exit_code, body, base_url
        if time.monotonic() >= deadline:
            return last_exit_code, last_body, base_url
        # The endpoint dropped between the health probe and the post: a reload edge.
        # Re-resolve before retrying instead of reporting a transport failure.
        _state, _probe_payload, new_base = _play_probe_endpoint(selector, args, base_url, health_timeout)
        if new_base:
            base_url = new_base
        time.sleep(min(unity_session.POLL_INTERVAL_SECONDS, max(deadline - time.monotonic(), 0.0)))


def _play_mode_absent(body):
    return isinstance(body, dict) and body.get("http_status") == 404


def _wait_for_play_state(operation, selector, args, session, base_url, target, timeout_seconds):
    """Poll health until the target state is reached.

    Returns ``(state, payload, base_url, blocker)``. ``state`` is the last observed
    play state (possibly ``None``); ``blocker`` is a modal blocker that stalled the
    transition, or ``None``. A transport failure is expected while a domain reload
    is in progress and is never reported as failure on its own.
    """
    health_timeout = getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    deadline = time.monotonic() + timeout_seconds
    state = None
    payload = None
    blocker = None
    next_blocker_check = time.monotonic() + 5.0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return state, payload, base_url, blocker
        probed, probed_payload, new_base = _play_probe_endpoint(selector, args, base_url, health_timeout)
        if new_base:
            base_url = new_base
        if probed is not None:
            state = probed
            payload = probed_payload
            if probed == target:
                return probed, payload, base_url, None
        now = time.monotonic()
        if now >= next_blocker_check:
            next_blocker_check = now + 5.0
            detected = _detect_exec_modal_blocker(session)
            if detected is not None:
                return state, payload, base_url, detected
        time.sleep(min(unity_session.POLL_INTERVAL_SECONDS, max(remaining, 0.0)))


def _play_transition(operation, pre_state):
    if operation == "play":
        if pre_state == PLAY_STATE_PAUSED:
            return "resumed"
        if pre_state == PLAY_STATE_PLAYING:
            return "already_in_state"
        return "performed"
    if operation == "pause":
        return "already_in_state" if pre_state == PLAY_STATE_PAUSED else "performed"
    return "already_in_state" if pre_state == PLAY_STATE_EDIT else "performed"


def _play_pre_settle(args, selector, session, base_url, recovery):
    """Settle pending code before entering play mode, without an exec request.

    Mirrors the exec refresh loop: ask the server for the refresh decision, settle
    the compile it starts, then re-ask so the compile gate can report a failing
    build instead of entering play mode on stale code. A settle that does not finish
    cleanly does not immediately give up: the endpoint can be down for the reload
    that ends the compile, so the loop keeps polling until the compile gate answers
    or the budget elapses. Returns ``(session, base_url, error_result, refresh_block)``
    where ``error_result`` is ``None`` when the Editor is safe to play and
    ``refresh_block`` discloses a refresh that actually ran.
    """
    refresh_block = None
    settle_attempted = False
    wait_ms = getattr(args, "wait_timeout_ms", direct_exec_client.DEFAULT_WAIT_TIMEOUT_MS)
    settle_budget = _post_refresh_ready_timeout_seconds(args)
    deadline = time.monotonic() + settle_budget + settle_budget
    while True:
        exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
            "refresh", base_url, {}, wait_ms
        )
        body = _parse_response_body(stdout_text, stderr_text)
        if _play_mode_absent(body):
            return session, base_url, _version_mismatch_result(
                args, cli_version.feature_missing_detail(base_url, feature="/refresh")
            ), refresh_block
        if _is_refresh_pending_response(exit_code, stdout_text):
            refresh_block = _extract_refresh_block(stdout_text) or refresh_block
            if not settle_attempted:
                settle_attempted = True
                settled = _settle_after_automatic_refresh(args, selector, session, base_url, recovery)
                if settled is not None:
                    session, base_url = settled
                    continue
            if time.monotonic() >= deadline:
                return session, base_url, (
                    EXIT_RUNNING,
                    emit_payload(_play_refreshing_payload(args, session, refresh_block)),
                    "",
                ), refresh_block
            time.sleep(unity_session.POLL_INTERVAL_SECONDS)
            continue
        if exit_code == EXIT_NOT_AVAILABLE:
            # The endpoint is down for the reload that ends the compile. Keep polling
            # so the compile gate (a failing build) can answer once it is back.
            if time.monotonic() >= deadline:
                return session, base_url, (
                    EXIT_RUNNING,
                    emit_payload(_play_refreshing_payload(args, session, refresh_block)),
                    "",
                ), refresh_block
            time.sleep(unity_session.POLL_INTERVAL_SECONDS)
            continue
        if exit_code == EXIT_UNITY_COMPILE_ERROR:
            stdout_text, stderr_text = _inject_guidance_into_response(
                stdout_text, stderr_text, "play", args
            )
            return session, base_url, (exit_code, stdout_text, stderr_text), refresh_block
        if exit_code != 0:
            stdout_text, stderr_text = _inject_guidance_into_response(
                stdout_text, stderr_text, "play", args
            )
            return session, base_url, (exit_code, stdout_text, stderr_text), refresh_block
        return session, base_url, None, refresh_block


def _play_refreshing_payload(args, session, refresh_block):
    payload = {
        "ok": True,
        "status": "running",
        "operation": "play",
        "phase": PHASE_REFRESHING,
    }
    if refresh_block is not None:
        payload["refresh"] = refresh_block
    if session is not None:
        payload["session"] = session.to_payload()
    _attach_guidance(payload, "play", "running", args)
    return attach_diagnostics(payload, include_diagnostics=args.include_diagnostics, session=session)


def _play_running_result(operation, session, args, state):
    payload = {
        "ok": True,
        "status": "running",
        "operation": operation,
        "phase": PHASE_PLAY_MODE,
        "play_state": state,
        "result": {"play_state": state},
    }
    if session is not None:
        payload["session"] = session.to_payload()
    _attach_guidance(payload, operation, "running", args)
    return EXIT_RUNNING, emit_payload(payload), ""


def _play_blocker_result(operation, session, args, blocker):
    payload = expected_failure_payload(
        operation,
        "modal_blocked",
        "a modal dialog is blocking the play-mode transition",
        session=session,
        include_diagnostics=args.include_diagnostics,
    )
    payload["blocker"] = blocker
    _attach_guidance(payload, operation, "modal_blocked", args)
    return EXIT_MODAL_BLOCKED, emit_payload(payload), ""


def _invalid_play_state_result(operation, session, args, body):
    state = _health_play_state(body)
    payload = expected_failure_payload(
        operation,
        "invalid_play_state",
        "pause requires the Editor to be in play mode",
        session=session,
        include_diagnostics=args.include_diagnostics,
    )
    payload["play_state"] = state
    payload["result"] = {"play_state": state}
    _attach_guidance(payload, operation, "invalid_play_state", args)
    return 1, emit_payload(payload), ""


def _play_success_result(operation, args, session, transition, play_state, force_run_in_background, project_setting, refresh_block=None):
    result = {"play_state": play_state, "transition": transition}
    if operation == "play":
        result["run_in_background"] = {
            "forced": bool(force_run_in_background),
            "project_setting": project_setting,
            "option": "--no-run-in-background",
        }
    payload = success_payload(operation, session=session, result=result, include_diagnostics=args.include_diagnostics)
    if refresh_block is not None:
        payload["refresh"] = refresh_block
    _attach_guidance(payload, operation, "completed", args)
    return 0, emit_payload(payload), ""


def _read_compile_error_total(base_url, args):
    exit_code, stdout_text, stderr_text = direct_exec_client.invoke_command(
        "get-compile-errors", base_url, {"start": 0, "count": 1}, 5000
    )
    body = _parse_response_body(stdout_text, stderr_text)
    if isinstance(body, dict):
        total = body.get("total")
        if isinstance(total, int):
            return total
    return 0


def _stop_wait_for_compile(selector, args, session, base_url, baseline, recovery):
    """Wait for the compile cycle deferred by a play-mode exit.

    Returns ``(compile_info, base_url)`` or ``(None, base_url)`` when the cycle did
    not settle in time. The generation baseline is checked first so a compile hidden
    behind the exit's domain reload is inferred even though ``compiling`` was never
    observable.
    """
    settle_timeout = _post_refresh_ready_timeout_seconds(args)
    holder = {"base_url": base_url}

    def probe(_ignored_base_url, health_timeout):
        _state, payload, new_base = _play_probe_endpoint(selector, args, holder["base_url"], health_timeout)
        if new_base:
            holder["base_url"] = new_base
        return payload, None

    cycle = wait_for_compile_cycle(
        holder["base_url"],
        getattr(args, "appear_timeout_seconds", unity_session.DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS),
        settle_timeout,
        getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS),
        probe_health_fn=probe,
        unity_pid=session.unity_pid if session is not None else None,
        compile_generation_baseline=baseline,
    )
    recovery.record(cycle.get("api_updater_declines", 0))
    outcome = cycle["outcome"]
    if outcome == COMPILE_OUTCOME_GENERATION:
        info = {"outcome": "compile_settled", "edge": COMPILE_EDGE_GENERATION_ADVANCE}
    elif outcome == COMPILE_OUTCOME_READY:
        info = {"outcome": "compile_settled"}
    elif outcome == COMPILE_OUTCOME_TIMEOUT:
        return None, holder["base_url"]
    else:
        info = {"outcome": "no_compile_observed"}
    return info, holder["base_url"]


def _stop_success_result(operation, selector, args, session, base_url, transition, baseline, pending, recovery):
    _state, payload, base_url = _play_probe_endpoint(
        selector, args, base_url, getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    )
    generation = _compile_generation_from_health(payload)
    compile_info = None
    if baseline is not None and generation is not None and generation > baseline:
        compile_info = {"outcome": "compile_settled", "edge": COMPILE_EDGE_GENERATION_ADVANCE}
    elif pending == "pending":
        compile_info, base_url = _stop_wait_for_compile(selector, args, session, base_url, baseline, recovery)
    else:
        compile_info = {"outcome": "no_compile_observed"}

    if compile_info is None:
        # The deferred compile did not settle in time. The play-state transition
        # succeeded, but the command cannot claim the exit is fully done.
        running = {
            "ok": True,
            "status": "running",
            "operation": operation,
            "phase": PHASE_COMPILING,
            "play_state": PLAY_STATE_EDIT,
            "result": {"play_state": PLAY_STATE_EDIT},
        }
        if session is not None:
            running["session"] = session.to_payload()
        _attach_guidance(running, operation, "running", args)
        return EXIT_RUNNING, emit_payload(running), ""

    if compile_info["outcome"] == "no_compile_observed":
        compile_info["compile_errors_total"] = 0
    else:
        compile_info["compile_errors_total"] = _read_compile_error_total(base_url, args)

    result = {"play_state": PLAY_STATE_EDIT, "transition": transition, "compile": compile_info}
    payload = success_payload(operation, session=session, result=result, include_diagnostics=args.include_diagnostics)
    _attach_guidance(payload, operation, "completed", args)
    if compile_info["compile_errors_total"] > 0:
        step = {
            "command": "get-compile-errors",
            "when": "read the compile errors the deferred compile just produced",
            "argv_template": ["unity-puer-exec", "get-compile-errors", "--project-path", "{project_path}"],
        }
        payload["next_steps"] = [step] + list(payload.get("next_steps") or [])
    return 0, emit_payload(payload), ""


def _play_mode_exit_code(body):
    """Formal exit code for a machine-readable non-success play-mode body.

    A body that carries an explicit ``exit_code`` (for example the boundary's
    ``empty_response`` payload) is authoritative; otherwise the shared
    status→exit-code mapping decides. This keeps distinct non-success states
    distinguishable by exit code alone.
    """
    explicit = body.get("exit_code")
    if isinstance(explicit, int) and not isinstance(explicit, bool):
        return explicit
    return direct_exec_client.status_to_exit_code(body)


def _run_play_mode_command(operation, args, recovery):
    action = operation
    selector = resolve_selector(args)
    validate_positive(args.timeout_seconds, "timeout-seconds")
    validate_project_mode_only(selector, "unity-exe-path", getattr(args, "unity_exe_path", None))
    validate_project_mode_only(selector, "unity-log-path", getattr(args, "unity_log_path", None))
    validate_project_mode_only(selector, "unity-launch-arg", getattr(args, "unity_launch_args", None))

    if selector == "project_path":
        _sweep_pending_exec(args)
        session = unity_session.ensure_session_ready(
            project_path=args.project_path,
            unity_exe_path=getattr(args, "unity_exe_path", None),
            unity_log_path=getattr(args, "unity_log_path", None),
            unity_launch_args=getattr(args, "unity_launch_args", None),
            argv0=getattr(args, "argv0", None),
        )
        recovery.record(getattr(session, "api_updater_declines", 0))
        session.api_updater_declines = 0
        base_url = session.base_url
    else:
        session = None
        base_url = args.base_url

    force_run_in_background = False
    refresh_block = None
    if operation == "play":
        force_run_in_background = not bool(getattr(args, "no_run_in_background", False))
        session, base_url, error_result, refresh_block = _play_pre_settle(
            args, selector, session, base_url, recovery
        )
        if error_result is not None:
            return error_result

    health_timeout = getattr(args, "health_timeout_seconds", unity_session.DEFAULT_HEALTH_TIMEOUT_SECONDS)
    pre_state, pre_payload, base_url = _play_probe_endpoint(selector, args, base_url, health_timeout)

    baseline = None
    pending = None
    if operation == "stop":
        baseline = _compile_generation_from_health(pre_payload)
        if isinstance(pre_payload, dict):
            refresh = pre_payload.get("refresh")
            if isinstance(refresh, dict):
                pending = refresh.get("pending")

    exit_code, body, base_url = _post_play_mode(
        selector, args, session, base_url, action, force_run_in_background
    )
    if _play_mode_absent(body):
        return _version_mismatch_result(args, cli_version.feature_missing_detail(base_url))
    if body is None:
        payload = expected_failure_payload(
            operation,
            "not_available",
            "the control endpoint did not answer the play-mode request",
            session=session,
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, operation, "not_available", args)
        return EXIT_NOT_AVAILABLE, emit_payload(payload), ""
    if body.get("status") == "invalid_play_state":
        return _invalid_play_state_result(operation, session, args, body)
    if not body.get("ok"):
        status = body.get("status", "failed")
        payload = expected_failure_payload(
            operation,
            status,
            body.get("error", "play-mode request failed"),
            session=session,
            include_diagnostics=args.include_diagnostics,
        )
        for key in ("blocker", "exit_code_meaning", "response_detail"):
            if key in body:
                payload[key] = body[key]
        _attach_guidance(payload, operation, status, args)
        return _play_mode_exit_code(body), emit_payload(payload), ""

    target = PLAY_ACTION_TARGET[action]
    exit_wait_seconds = float(args.timeout_seconds)
    if operation == "stop":
        exit_wait_seconds = max(exit_wait_seconds, _post_refresh_ready_timeout_seconds(args))
    state, _state_payload, base_url, blocker = _wait_for_play_state(
        operation, selector, args, session, base_url, target, exit_wait_seconds
    )
    if state != target:
        if blocker is not None:
            return _play_blocker_result(operation, session, args, blocker)
        return _play_running_result(operation, session, args, state)

    transition = _play_transition(operation, pre_state)
    if operation == "stop":
        return _stop_success_result(
            operation, selector, args, session, base_url, transition, baseline, pending, recovery
        )
    return _play_success_result(
        operation,
        args,
        session,
        transition,
        target,
        force_run_in_background,
        body.get("project_run_in_background"),
        refresh_block=refresh_block,
    )


def run_play(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_play_mode_command("play", args, recovery)
    return _apply_api_updater_warning(result, recovery)


def run_pause(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_play_mode_command("pause", args, recovery)
    return _apply_api_updater_warning(result, recovery)


def run_stop(args):
    recovery = _ApiUpdaterRecovery()
    result = _run_play_mode_command("stop", args, recovery)
    return _apply_api_updater_warning(result, recovery)


def run_ensure_closed(args):
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
        stopped, session = unity_session.ensure_closed(project_path=args.project_path, mode=mode, timeout_seconds=args.timeout_seconds, argv0=getattr(args, "argv0", None))
    else:
        stopped, session = unity_session.ensure_closed(base_url=args.base_url, mode="inspect", timeout_seconds=args.timeout_seconds)

    if not stopped:
        payload = expected_failure_payload(
            "ensure-closed",
            "not_stopped",
            "target is not stopped",
            session=session,
            include_diagnostics=args.include_diagnostics,
        )
        _attach_guidance(payload, args.command, "not_stopped", args)
        _mark_deprecated(payload, args.command)
        return EXIT_NOT_STOPPED, emit_payload(payload), ""

    payload = success_payload(
        "ensure-closed",
        session=session,
        result={"status": "stopped"},
        include_diagnostics=args.include_diagnostics,
    )
    _mark_deprecated(payload, args.command)
    return 0, emit_payload(payload), ""


def _mark_deprecated(payload, command):
    """Add the alias-deprecation field when ``command`` is a deprecated alias."""
    deprecation = command_registry.deprecation_for(command)
    if deprecation is not None and isinstance(payload, dict):
        payload["deprecated"] = deprecation
    return payload


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




def _extract_compile_errors_from_log(log_path, max_errors=20):
    """Extract C# compile errors from a Unity Editor log file."""
    import re
    if not log_path:
        return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return None
    # Matches: file(line,col): error [CODE]: message
    # Error code (e.g. CS1003) is optional; some Unity errors omit it.
    # The +? on the file path is non-greedy so paths with parentheses still match.
    error_pattern = re.compile(
        r"^(.+?)\((\d+),(\d+)\):\s*error\s+(?:([A-Z]+\d+):\s*)?(.+)$"
    )
    errors = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n\r")
        m = error_pattern.match(line)
        if m:
            filepath = m.group(1)
            line_no = int(m.group(2))
            col = int(m.group(3))
            code = m.group(4)  # may be None for uncoded errors
            msg = m.group(5)
            # Strip leading ": " when no error code was matched
            if msg and msg.startswith(": "):
                msg = msg[2:]
            # Collect continuation lines (indented, not a new error)
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")) and not error_pattern.match(lines[i].strip()):
                continuation = lines[i].rstrip("\n\r")
                if continuation.strip():
                    msg += "\n" + continuation.strip()
                i += 1
            errors.append({
                "file": filepath,
                "line": line_no,
                "column": col,
                "code": code or None,
                "message": msg,
            })
        else:
            i += 1
    if not errors:
        return None
    return {
        "total_errors": len(errors),
        "errors": errors[:max_errors],
    }


def _normalize_exec_blocker_result(exit_code, stdout_text, stderr_text, session, log_path=None):
    if session is None or not stdout_text:
        return exit_code, stdout_text, stderr_text
    body = json.loads(stdout_text)
    if not _should_check_exec_blocker(exit_code, body):
        return exit_code, stdout_text, stderr_text

    # ScriptUpdater consent dialog: auto-decline (No) and keep the original status.
    # The agent must never see this as modal_blocked or need resolve-blocker.
    dismissed = _dismiss_api_updater_for_pid(session.unity_pid)
    if dismissed:
        session.api_updater_declines = getattr(session, "api_updater_declines", 0) + dismissed
        return exit_code, emit_payload(_attach_api_updater_warning(body)), stderr_text

    blocker = _detect_exec_modal_blocker(session)
    if blocker is None:
        return exit_code, stdout_text, stderr_text

    # Safe Mode: auto-dismiss and return as compile errors so Agent never sees modal_blocked
    if blocker.get("type") == "safe_mode_dialog":
        # Auto-click "Enter Safe Mode" if the dialog is still showing
        try:
            resolve_result = unity_modal_blockers.resolve_modal_blocker(
                session.unity_pid, action="cancel", timeout_ms=3000
            )
        except Exception:
            resolve_result = {"ok": False}
        # Extract compile errors from log
        compile_info = _extract_compile_errors_from_log(log_path) if log_path else None
        normalized = {
            "ok": False,
            "status": "unity_compile_error",
            "request_id": body.get("request_id"),
            "compile_errors_total": 0,
            "compile_warnings_total": 0,
            "compile_messages": [],
        }
        if compile_info:
            normalized["compile_errors_total"] = compile_info["total_errors"]
            normalized["compile_messages"] = compile_info["errors"]
        if "diagnostics" in body:
            normalized["diagnostics"] = body["diagnostics"]
        return direct_exec_client.EXIT_UNITY_COMPILE_ERROR, emit_payload(normalized), ""

    # Other modal blockers: report as before
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
