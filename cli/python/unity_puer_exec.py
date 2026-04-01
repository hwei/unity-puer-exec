#!/usr/bin/env python3
import sys

import unity_puer_exec_runtime as runtime
import unity_puer_exec_surface as surface


EXIT_RUNNING = runtime.EXIT_RUNNING
EXIT_COMPILING = runtime.EXIT_COMPILING
EXIT_NOT_AVAILABLE = runtime.EXIT_NOT_AVAILABLE
EXIT_MISSING = runtime.EXIT_MISSING
EXIT_SESSION_STATE = runtime.EXIT_SESSION_STATE
EXIT_NO_OBSERVATION_TARGET = runtime.EXIT_NO_OBSERVATION_TARGET
EXIT_NOT_STOPPED = runtime.EXIT_NOT_STOPPED
EXIT_UNITY_START_FAILED = runtime.EXIT_UNITY_START_FAILED
EXIT_UNITY_NOT_READY = runtime.EXIT_UNITY_NOT_READY
EXIT_MODAL_BLOCKED = runtime.EXIT_MODAL_BLOCKED
RESULT_MARKER_PREFIX = runtime.RESULT_MARKER_PREFIX
RESULT_MARKER_PATTERN = runtime.RESULT_MARKER_PATTERN
direct_exec_client = runtime.direct_exec_client


def _build_parser():
    return surface.build_parser()


def run_cli(argv, argv0=None):
    return runtime.run_cli(argv, surface, argv0=argv0)


def main():
    exit_code, stdout_text, stderr_text = run_cli(sys.argv[1:], argv0=sys.argv[0])
    if stdout_text:
        print(stdout_text)
    if stderr_text:
        print(stderr_text, file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
