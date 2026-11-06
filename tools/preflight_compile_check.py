#!/usr/bin/env python3
"""Non-interactive compile preflight for the real-host validation suite.

A package compile error cannot be reported to the real-host suite by the
interactive launch itself: the Editor intercepts it with the Safe Mode dialog,
which blocks an unattended run. ``Unity -batchMode -quit -nographics`` runs the
same import and script-compilation pipeline without an interactive session,
writes the compiler diagnostics to the project-private ``-logFile``, and exits.
That turns a package compile error into a fast, named failure before the
interactive Editor is ever launched.

The helper resolves the host and the Editor through the same paths the suite
already uses (``prepare_validation_host`` / ``unity_session``) and appends the
``.env`` launch-argument input, so a host that needs project-specific switches
compiles under the same conditions as its interactive launch.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import prepare_validation_host


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_session  # type: ignore  # noqa: E402
import unity_session_process  # type: ignore  # noqa: E402


STATUS_SKIPPED = "skipped"
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"

KIND_COMPILE_FAILURE = "compile_failure"
KIND_LAUNCH_FAILURE = "launch_failure"
KIND_TIMEOUT = "timeout"
# The assembly compiled, but against an API the dependency has retired. A
# distinct kind lets a caller tell that apart from "did not compile" without
# parsing messages.
KIND_PACKAGE_DEPRECATION = "package_deprecation"
# Only reachable through ``--strict-package-warnings``, which escalates every
# package-attributable warning rather than just the deprecation codes.
KIND_PACKAGE_WARNING = "package_warning"

# The narrow default fail-set: the codes that proved both silent and
# load-bearing. A one-sided versionDefines expression that selected a retired
# API still compiles, so only the warning can name the mistake.
DEPRECATION_WARNING_CODES = frozenset({"CS0618", "CS0619"})

PACKAGE_NAME = "com.txcombo.unity-puer-exec"
_PACKAGE_NAME_LOWER = PACKAGE_NAME.lower()
# Compared against lower-cased path components, so this covers ``packages`` and
# ``Packages`` -- including logs that mix ``\`` and ``/`` separators.
_PACKAGE_PARENT_DIRECTORIES = frozenset({"packages"})

DEFAULT_TIMEOUT_SECONDS = 1800.0
# Project-private log, next to the CLI-launched interactive log. Under Temp/
# because it is observation surface for a run, not an archive.
PREFLIGHT_LOG_RELATIVE_PATH = ("Temp", "UnityPuerExec", "preflight_compile.log")

# ``Assets/Foo.cs(12,25): error CS0103: The name `Bar' does not exist ...``
# and the warning sibling ``...: warning CS0618: 'JsEnv' is obsolete ...``.
# One severity-aware pattern keeps the location handling shared: the error and
# warning parsers differ only by which severity they keep.
_DIAGNOSTIC_RE = re.compile(
    r"\b(?P<severity>error|warning)\s+(?P<code>CS\d+)\s*:\s*(?P<message>.*)$"
)
# The optional location prefix that precedes ``error CS...`` on the same line.
_LOCATION_RE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)(?:,(?P<column>\d+))?\)\s*:\s*$"
)


def preflight_log_path(project_path):
    return Path(project_path).joinpath(*PREFLIGHT_LOG_RELATIVE_PATH)


def _parse_diagnostics(log_text, severity):
    """Extract structured ``<severity> CS`` diagnostics from a Unity log body.

    Returns one entry per matching line, in log order. ``file``/``line``/
    ``column`` are ``None`` when the compiler reported a diagnostic without a
    source location (for example ``error CS2001: Source file '...' could not be
    found``), so the caller always gets the code and message.
    """
    diagnostics = []
    for raw_line in str(log_text or "").splitlines():
        match = _DIAGNOSTIC_RE.search(raw_line)
        # Unity emits one diagnostic per line, but a line that mentions another
        # severity first must not hide the one being requested: advance from the
        # rejected match instead of stopping. Matching the *first* diagnostic of
        # the requested severity keeps this byte-identical to the pre-warning
        # parser for every log an error-only reader already handled.
        while match is not None and match.group("severity") != severity:
            match = _DIAGNOSTIC_RE.search(raw_line, match.start() + 1)
        if match is None:
            continue
        prefix = raw_line[: match.start()].strip()
        location = _LOCATION_RE.match(prefix)
        file_path = None
        line_number = None
        column_number = None
        if location is not None:
            file_path = location.group("file").strip() or None
            line_number = int(location.group("line"))
            raw_column = location.group("column")
            column_number = int(raw_column) if raw_column else None
        diagnostics.append(
            {
                "code": match.group("code"),
                "message": match.group("message").strip(),
                "file": file_path,
                "line": line_number,
                "column": column_number,
            }
        )
    return diagnostics


def parse_compile_errors(log_text):
    """Extract structured ``error CS`` diagnostics from a Unity log body.

    ``diagnostics`` in the result payload means ``error CS`` only; warnings are
    reported separately by :func:`parse_package_warnings`.
    """
    return _parse_diagnostics(log_text, "error")


def _path_components(file_path):
    if file_path is None:
        return []
    text = str(file_path).strip()
    if not text:
        return []
    return [component for component in text.replace("\\", "/").split("/") if component]


def is_package_source_file(file_path):
    """Decide whether a diagnostic's ``file`` belongs to this package.

    A diagnostic belongs to the package when its normalized path carries the
    package-name component under a ``packages``/``Packages`` directory. Matching
    the path component instead of an absolute prefix is what keeps attribution
    working for both host wirings: a ``file:`` manifest entry logs the repository
    path, while an embedded copy logs a path under the host's own ``Packages/``
    directory. A diagnostic with no location cannot be attributed, so it is never
    claimed.
    """
    components = _path_components(file_path)
    lowered = [component.lower() for component in components]
    for index in range(len(lowered) - 1):
        if (
            lowered[index] in _PACKAGE_PARENT_DIRECTORIES
            and lowered[index + 1] == _PACKAGE_NAME_LOWER
        ):
            return True
    return False


def parse_package_warnings(log_text):
    """Extract ``warning CS`` diagnostics attributable to this package.

    Same entry shape as :func:`parse_compile_errors`. Warnings whose source
    location is outside this package, or absent, are dropped so the host's own
    warnings and third-party package noise can neither satisfy nor trip the gate.
    """
    return [
        warning
        for warning in _parse_diagnostics(log_text, "warning")
        if is_package_source_file(warning.get("file"))
    ]


def _is_deprecation_warning(diagnostic):
    return diagnostic.get("code") in DEPRECATION_WARNING_CODES


def _format_diagnostic_lines(entries, severity):
    lines = []
    for diagnostic in entries:
        location = diagnostic.get("file") or "<no source location>"
        line_number = diagnostic.get("line")
        column_number = diagnostic.get("column")
        position = ""
        if line_number is not None:
            position = "({},{})".format(
                line_number, column_number if column_number is not None else "?"
            )
        lines.append(
            "{}{}: {} {}: {}".format(
                location,
                position,
                severity,
                diagnostic.get("code"),
                diagnostic.get("message"),
            )
        )
    return lines


def format_failure_detail(result):
    """Render a failed preflight result as a multi-line, human-usable detail."""
    diagnostics = result.get("diagnostics") or []
    if diagnostics:
        lines = [
            "package compile preflight failed with {} `error CS` diagnostic(s):".format(
                len(diagnostics)
            )
        ]
        lines.extend(_format_diagnostic_lines(diagnostics, "error"))
        return "\n".join(lines)

    package_warnings = result.get("package_warnings") or []
    kind = result.get("kind")
    if package_warnings and kind in (KIND_PACKAGE_DEPRECATION, KIND_PACKAGE_WARNING):
        if kind == KIND_PACKAGE_DEPRECATION:
            failing = [w for w in package_warnings if _is_deprecation_warning(w)]
            failing = failing or package_warnings
            lines = [
                "package compile preflight failed with {} package deprecation "
                "warning(s) (CS0618, CS0619):".format(len(failing))
            ]
        else:
            failing = package_warnings
            lines = [
                "package compile preflight failed with {} package warning(s) "
                "under --strict-package-warnings:".format(len(failing))
            ]
        lines.extend(_format_diagnostic_lines(failing, "warning"))
        return "\n".join(lines)

    reason = result.get("reason") or "batch compile preflight failed"
    return "{} (exit_code={}; log: {})".format(
        reason, result.get("exit_code"), result.get("log_path")
    )


def _skipped(reason, project_path=None, unity_exe_path=None):
    return {
        "status": STATUS_SKIPPED,
        "kind": None,
        "reason": reason,
        "exit_code": None,
        "log_path": None,
        "diagnostics": [],
        "package_warnings": [],
        "project_path": None if project_path is None else str(project_path),
        "unity_exe_path": None if unity_exe_path is None else str(unity_exe_path),
    }


def _read_log_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def run_preflight(
    project_path=None,
    unity_exe_path=None,
    env=None,
    log_path=None,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    strict_package_warnings=False,
    resolve_project_path_fn=None,
    resolve_unity_exe_path_fn=None,
    run_fn=None,
    read_log_fn=None,
):
    """Compile-check the validation host in batch mode and report the outcome.

    Returns a structured result. ``status`` is ``skipped`` when a prerequisite is
    unavailable (the suite's existing skip conditions), ``passed`` when the batch
    Editor exited cleanly with no compiler errors and no deprecation diagnostic
    attributable to this package, and ``failed`` otherwise -- carrying the parsed
    ``error CS`` diagnostics (``kind=compile_failure``), the package-attributable
    warnings that failed the run (``kind=package_deprecation``, or
    ``kind=package_warning`` under ``strict_package_warnings``), the bare exit
    code and log path (``kind=launch_failure``), or a timeout. ``package_warnings``
    always carries every package-attributable warning found, whether or not it
    failed the run; ``diagnostics`` keeps meaning ``error CS`` only.
    """
    env = os.environ if env is None else env
    resolve_project_path_fn = (
        prepare_validation_host.resolve_project_path
        if resolve_project_path_fn is None
        else resolve_project_path_fn
    )
    resolve_unity_exe_path_fn = (
        unity_session._resolve_unity_exe_path
        if resolve_unity_exe_path_fn is None
        else resolve_unity_exe_path_fn
    )
    run_fn = subprocess.run if run_fn is None else run_fn
    read_log_fn = _read_log_text if read_log_fn is None else read_log_fn

    try:
        resolved_project_path = Path(resolve_project_path_fn(project_path))
    except ValueError as exc:
        return _skipped("validation host project path unavailable: {}".format(exc))
    if not resolved_project_path.exists():
        return _skipped(
            "validation host project path does not exist: {}".format(resolved_project_path)
        )

    manifest_path = prepare_validation_host.project_path_to_manifest_path(resolved_project_path)
    if not manifest_path.exists():
        return _skipped("validation host manifest is missing: {}".format(manifest_path))

    try:
        resolved_unity_exe_path = resolve_unity_exe_path_fn(resolved_project_path, unity_exe_path)
    except Exception as exc:  # noqa: BLE001 - normalize any launcher resolution failure.
        return _skipped(
            "Unity executable unavailable: {}".format(exc), project_path=resolved_project_path
        )

    try:
        launch_args = unity_session_process.parse_ambient_unity_launch_args(env=env)
    except Exception as exc:  # noqa: BLE001 - config input, not a product failure.
        return _skipped(
            "Unity launch arguments unavailable: {}".format(exc),
            project_path=resolved_project_path,
            unity_exe_path=resolved_unity_exe_path,
        )

    resolved_log_path = (
        Path(log_path) if log_path else preflight_log_path(resolved_project_path)
    )
    try:
        resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_log_path.write_text("", encoding="utf-8")
    except OSError:
        # Unity creates the file itself; a stale file is only a stale diagnostic risk.
        pass

    argv = [
        str(resolved_unity_exe_path),
        "-batchMode",
        "-quit",
        "-nographics",
        "-projectPath",
        str(resolved_project_path),
        "-logFile",
        str(resolved_log_path),
    ] + list(launch_args)

    try:
        completed = run_fn(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        log_text = read_log_fn(resolved_log_path)
        return {
            "status": STATUS_FAILED,
            "kind": KIND_TIMEOUT,
            "reason": "batch compile preflight timed out after {}s".format(timeout_seconds),
            "exit_code": None,
            "log_path": str(resolved_log_path),
            "diagnostics": parse_compile_errors(log_text),
            "package_warnings": parse_package_warnings(log_text),
            "project_path": str(resolved_project_path),
            "unity_exe_path": str(resolved_unity_exe_path),
        }
    except OSError as exc:
        return _skipped(
            "failed to launch Unity batch preflight: {}".format(exc),
            project_path=resolved_project_path,
            unity_exe_path=resolved_unity_exe_path,
        )

    exit_code = completed.returncode
    log_text = read_log_fn(resolved_log_path)
    diagnostics = parse_compile_errors(log_text)
    package_warnings = parse_package_warnings(log_text)
    deprecation_warnings = [
        warning for warning in package_warnings if _is_deprecation_warning(warning)
    ]
    # Escalation only turns a warning into a failure; the deprecation fail-set
    # already applies on its own. A non-zero exit is a launch failure in its own
    # right, so it is not relabelled as an escalation of a warning.
    strict_failure = bool(strict_package_warnings and package_warnings and exit_code == 0)

    if exit_code == 0 and not diagnostics and not deprecation_warnings and not strict_failure:
        return {
            "status": STATUS_PASSED,
            "kind": None,
            "reason": None,
            "exit_code": 0,
            "log_path": str(resolved_log_path),
            "diagnostics": [],
            "package_warnings": package_warnings,
            "project_path": str(resolved_project_path),
            "unity_exe_path": str(resolved_unity_exe_path),
        }

    if diagnostics:
        kind = KIND_COMPILE_FAILURE
        reason = "package compile preflight reported {} error(s)".format(len(diagnostics))
    elif deprecation_warnings:
        kind = KIND_PACKAGE_DEPRECATION
        reason = (
            "package compile preflight reported {} package deprecation "
            "diagnostic(s) (CS0618, CS0619)"
        ).format(len(deprecation_warnings))
    elif strict_failure:
        kind = KIND_PACKAGE_WARNING
        reason = (
            "package compile preflight reported {} package warning(s) "
            "under --strict-package-warnings"
        ).format(len(package_warnings))
    else:
        kind = KIND_LAUNCH_FAILURE
        reason = "batch compile preflight exited non-zero with no `error CS` diagnostic"
    return {
        "status": STATUS_FAILED,
        "kind": kind,
        "reason": reason,
        "exit_code": exit_code,
        "log_path": str(resolved_log_path),
        "diagnostics": diagnostics,
        "package_warnings": package_warnings,
        "project_path": str(resolved_project_path),
        "unity_exe_path": str(resolved_unity_exe_path),
    }


_PREFLIGHT_RESULT = None


def run_preflight_once(project_path=None, unity_exe_path=None, **kwargs):
    """Run the preflight at most once per process, caching the first result.

    The real-host suite launches one interactive Editor per test class, so a
    per-class preflight would multiply the batch launch cost. The cached result
    keeps the added cost a single batch launch per suite invocation.
    """
    global _PREFLIGHT_RESULT
    if _PREFLIGHT_RESULT is None:
        _PREFLIGHT_RESULT = run_preflight(project_path, unity_exe_path, **kwargs)
    return _PREFLIGHT_RESULT


def reset_preflight_cache():
    global _PREFLIGHT_RESULT
    _PREFLIGHT_RESULT = None


def require_preflight(project_path=None, unity_exe_path=None, **kwargs):
    """Run the once-per-process preflight and raise when it does not pass.

    A compile failure raises with the parsed ``error CS`` diagnostics before any
    interactive Editor is launched, so a package compile error is named rather
    than reaching the Editor's Safe Mode dialog. A package-attributable
    deprecation diagnostic raises with the same multi-line detail, and says it is
    a deprecation rather than a compile error. A batch launch that cannot
    complete raises too: the skip conditions (gate, host project, manifest,
    Editor executable) are checked first, so reaching this point means they were
    satisfied.
    """
    result = run_preflight_once(project_path, unity_exe_path, **kwargs)
    if result["status"] == STATUS_FAILED:
        raise AssertionError(format_failure_detail(result))
    return result


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Compile-check the validation host under Unity -batchMode before launching "
            "an interactive Editor for a real-host run."
        )
    )
    parser.add_argument(
        "--project-path",
        help="Path to the validation host Unity Project directory. Defaults to UNITY_PROJECT_PATH or .env.",
    )
    parser.add_argument(
        "--unity-exe-path",
        help="Override the Unity executable path. Defaults to the host's Editor version.",
    )
    parser.add_argument(
        "--log-path",
        help="Override the batch log path. Defaults to <project>/Temp/UnityPuerExec/preflight_compile.log.",
    )
    parser.add_argument(
        "--strict-package-warnings",
        action="store_true",
        help=(
            "Fail on any warning attributable to this package, not only the "
            "deprecation codes CS0618/CS0619."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Maximum wall time for the batch compile. Defaults to {}.".format(
            DEFAULT_TIMEOUT_SECONDS
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_preflight(
        project_path=args.project_path,
        unity_exe_path=args.unity_exe_path,
        log_path=args.log_path,
        timeout_seconds=args.timeout_seconds,
        strict_package_warnings=args.strict_package_warnings,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == STATUS_FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
