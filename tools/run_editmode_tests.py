#!/usr/bin/env python3
"""Run the package's EditMode tests in Unity batch mode.

The EditMode assembly at ``packages/com.txcombo.unity-puer-exec/Tests/EditMode``
covers pure server-side behavior -- the exec refresh-block retention and the terminal
response rendering it feeds -- that the real-host suite only reaches through a live
Editor play-mode case. That case needs a prepared host and costs several minutes, so
this runner gives the same behavior a fast, Unity-side signal.

It reuses the batch-mode launch approach of ``tools/preflight_compile_check.py``: the
host and the Editor are resolved through ``prepare_validation_host`` /
``unity_session``, and the ``.env`` launch-argument input is appended, so the tests
compile and run under the same conditions as the interactive launch. ``-runTests``
makes the Editor exit once the run finishes, so ``-quit`` is deliberately not passed.

The run is scoped to the package's own test assembly (``-assemblyNames``) so an
unrelated EditMode test in the host project cannot fail this harness, and so an
undiscovered package assembly shows up as ``no_tests_discovered`` rather than as a
silent success.

This harness stays outside the default Python unit-test workflow: it needs a Unity
Editor and a prepared validation host project.
"""
import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
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

KIND_TEST_FAILURES = "test_failures"
KIND_NO_TESTS_DISCOVERED = "no_tests_discovered"
KIND_MISSING_RESULTS = "missing_results"
KIND_LAUNCH_FAILURE = "launch_failure"
KIND_TIMEOUT = "timeout"

EDITMODE_TEST_ASSEMBLY = "UnityPuerExec.EditMode.Tests"

DEFAULT_TIMEOUT_SECONDS = 1800.0
# Project-private observation surface, next to the preflight compile log. Under Temp/
# because it is a run artifact, not an archive.
EDITMODE_LOG_RELATIVE_PATH = ("Temp", "UnityPuerExec", "editmode_tests.log")
EDITMODE_RESULTS_RELATIVE_PATH = ("Temp", "UnityPuerExec", "editmode_test_results.xml")

_TERMINAL_RESULTS = ("Passed", "Skipped", "Inconclusive")


def editmode_log_path(project_path):
    return Path(project_path).joinpath(*EDITMODE_LOG_RELATIVE_PATH)


def editmode_results_path(project_path):
    return Path(project_path).joinpath(*EDITMODE_RESULTS_RELATIVE_PATH)


def parse_test_results(results_path):
    """Summarize a Unity/NUnit ``-testResults`` XML file.

    Returns the run totals plus one entry per non-passing case, so a failing test is
    named in the tool output instead of only visible in the XML. A missing or
    unparseable file yields ``None`` so the caller can distinguish "Unity never wrote
    results" from "the run reported failures".
    """
    path = Path(results_path)
    if not path.exists():
        return None
    try:
        root = ElementTree.parse(str(path)).getroot()
    except (ElementTree.ParseError, OSError):
        return None

    def _int(attribute):
        raw = root.get(attribute)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    summary = {
        "result": root.get("result"),
        "total": _int("total"),
        "passed": _int("passed"),
        "failed": _int("failed"),
        "skipped": _int("skipped"),
        "inconclusive": _int("inconclusive"),
        "failed_tests": [],
    }
    for case in root.iter("test-case"):
        result = case.get("result")
        if result in _TERMINAL_RESULTS:
            continue
        failure = case.find("failure")
        message = ""
        if failure is not None:
            message = (failure.get("message") or "").strip() or (failure.text or "").strip()
        summary["failed_tests"].append(
            {
                "name": case.get("name") or "",
                "result": result or "",
                "message": message.splitlines()[0] if message else "",
            }
        )
    return summary


def format_failure_detail(result):
    """Render a failed EditMode run as a multi-line, human-usable detail."""
    failed_tests = result.get("failed_tests") or []
    if failed_tests:
        lines = ["EditMode tests failed: {} case(s)".format(len(failed_tests))]
        for case in failed_tests:
            message = case.get("message") or ""
            lines.append(
                "{}: {}{}".format(
                    case.get("name") or "<unnamed>",
                    case.get("result") or "Failed",
                    ": {}".format(message) if message else "",
                )
            )
        return "\n".join(lines)
    return "{} (exit_code={}; log: {}; results: {})".format(
        result.get("reason"),
        result.get("exit_code"),
        result.get("log_path"),
        result.get("results_path"),
    )


def _skipped(reason, project_path=None, unity_exe_path=None):
    return {
        "status": STATUS_SKIPPED,
        "kind": None,
        "reason": reason,
        "exit_code": None,
        "log_path": None,
        "results_path": None,
        "total": None,
        "passed": None,
        "failed": None,
        "skipped": None,
        "inconclusive": None,
        "failed_tests": [],
        "project_path": None if project_path is None else str(project_path),
        "unity_exe_path": None if unity_exe_path is None else str(unity_exe_path),
    }


def _result(status, kind, reason, exit_code, log_path, results_path, summary, project_path, unity_exe_path):
    return {
        "status": status,
        "kind": kind,
        "reason": reason,
        "exit_code": exit_code,
        "log_path": None if log_path is None else str(log_path),
        "results_path": None if results_path is None else str(results_path),
        "total": None if summary is None else summary.get("total"),
        "passed": None if summary is None else summary.get("passed"),
        "failed": None if summary is None else summary.get("failed"),
        "skipped": None if summary is None else summary.get("skipped"),
        "inconclusive": None if summary is None else summary.get("inconclusive"),
        "failed_tests": [] if summary is None else summary.get("failed_tests") or [],
        "project_path": None if project_path is None else str(project_path),
        "unity_exe_path": None if unity_exe_path is None else str(unity_exe_path),
    }


def run_editmode_tests(
    project_path=None,
    unity_exe_path=None,
    env=None,
    log_path=None,
    results_path=None,
    assembly_names=EDITMODE_TEST_ASSEMBLY,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    resolve_project_path_fn=None,
    resolve_unity_exe_path_fn=None,
    run_fn=None,
    parse_results_fn=None,
):
    """Run the package EditMode tests in batch mode and report the outcome.

    ``status`` is ``skipped`` when a prerequisite is unavailable (the same skip
    conditions the real-host suite uses), ``passed`` when Unity exited cleanly and the
    results file reports no failures with at least one executed test, and ``failed``
    otherwise -- carrying the named failing cases, a missing-results signal, a launch
    failure, or a timeout.
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
    parse_results_fn = parse_test_results if parse_results_fn is None else parse_results_fn

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

    resolved_log_path = Path(log_path) if log_path else editmode_log_path(resolved_project_path)
    resolved_results_path = (
        Path(results_path) if results_path else editmode_results_path(resolved_project_path)
    )
    for path in (resolved_log_path, resolved_results_path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    # A stale results file would be parsed as this run's outcome if Unity never
    # rewrites it, so clear it before the launch.
    try:
        resolved_results_path.unlink()
    except OSError:
        pass
    try:
        resolved_log_path.write_text("", encoding="utf-8")
    except OSError:
        pass

    argv = [
        str(resolved_unity_exe_path),
        "-batchMode",
        "-nographics",
        "-projectPath",
        str(resolved_project_path),
        "-logFile",
        str(resolved_log_path),
        "-runTests",
        "-testPlatform",
        "EditMode",
        "-testResults",
        str(resolved_results_path),
    ]
    if assembly_names:
        argv.extend(["-assemblyNames", assembly_names])
    argv.extend(launch_args)

    try:
        completed = run_fn(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _result(
            STATUS_FAILED,
            KIND_TIMEOUT,
            "EditMode test run timed out after {}s".format(timeout_seconds),
            None,
            resolved_log_path,
            resolved_results_path,
            parse_results_fn(resolved_results_path),
            resolved_project_path,
            resolved_unity_exe_path,
        )
    except OSError as exc:
        return _skipped(
            "failed to launch Unity batch EditMode run: {}".format(exc),
            project_path=resolved_project_path,
            unity_exe_path=resolved_unity_exe_path,
        )

    exit_code = completed.returncode
    summary = parse_results_fn(resolved_results_path)

    if summary is None:
        return _result(
            STATUS_FAILED,
            KIND_MISSING_RESULTS,
            "Unity exited without writing test results (exit_code={})".format(exit_code),
            exit_code,
            resolved_log_path,
            resolved_results_path,
            None,
            resolved_project_path,
            resolved_unity_exe_path,
        )

    total = summary.get("total")
    failed = summary.get("failed") or 0
    if failed or summary.get("failed_tests"):
        return _result(
            STATUS_FAILED,
            KIND_TEST_FAILURES,
            "EditMode test run reported {} failing case(s)".format(
                len(summary.get("failed_tests") or []) or failed
            ),
            exit_code,
            resolved_log_path,
            resolved_results_path,
            summary,
            resolved_project_path,
            resolved_unity_exe_path,
        )

    if not total:
        return _result(
            STATUS_FAILED,
            KIND_NO_TESTS_DISCOVERED,
            "no EditMode tests were discovered for assembly '{}'".format(assembly_names),
            exit_code,
            resolved_log_path,
            resolved_results_path,
            summary,
            resolved_project_path,
            resolved_unity_exe_path,
        )

    if exit_code != 0:
        return _result(
            STATUS_FAILED,
            KIND_LAUNCH_FAILURE,
            "batch EditMode run exited non-zero with no reported test failure",
            exit_code,
            resolved_log_path,
            resolved_results_path,
            summary,
            resolved_project_path,
            resolved_unity_exe_path,
        )

    return _result(
        STATUS_PASSED,
        None,
        None,
        exit_code,
        resolved_log_path,
        resolved_results_path,
        summary,
        resolved_project_path,
        resolved_unity_exe_path,
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run the package's EditMode tests in Unity batch mode against the "
            "validation host project."
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
        help=(
            "Override the batch log path. Defaults to "
            "<project>/Temp/UnityPuerExec/editmode_tests.log."
        ),
    )
    parser.add_argument(
        "--results-path",
        help=(
            "Override the test-results XML path. Defaults to "
            "<project>/Temp/UnityPuerExec/editmode_test_results.xml."
        ),
    )
    parser.add_argument(
        "--assembly-names",
        default=EDITMODE_TEST_ASSEMBLY,
        help=(
            "Semicolon-separated test assemblies to run. Defaults to {}.".format(
                EDITMODE_TEST_ASSEMBLY
            )
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Maximum wall time for the test run. Defaults to {}.".format(
            DEFAULT_TIMEOUT_SECONDS
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_editmode_tests(
        project_path=args.project_path,
        unity_exe_path=args.unity_exe_path,
        log_path=args.log_path,
        results_path=args.results_path,
        assembly_names=args.assembly_names,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == STATUS_FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
