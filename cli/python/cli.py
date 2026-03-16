#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
import uuid


EXIT_RUNNING = 10
EXIT_COMPILING = 11
EXIT_NOT_AVAILABLE = 12
EXIT_MISSING = 13
EXIT_SESSION_STATE = 14

DEFAULT_BASE_URL = "http://127.0.0.1:55231"
DEFAULT_WAIT_TIMEOUT_MS = 1000
HTTP_TIMEOUT_BUFFER_SECONDS = 5.0


class HttpTransport:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def post_json(self, url, payload, timeout_seconds):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener.open(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def _status_to_exit_code(payload):
    if payload.get("ok"):
        if payload.get("status") == "running":
            return EXIT_RUNNING
        return 0

    status = payload.get("status")
    if status == "compiling":
        return EXIT_COMPILING
    if status == "not_available":
        return EXIT_NOT_AVAILABLE
    if status == "missing":
        return EXIT_MISSING
    if status in ("session_missing", "session_stale"):
        return EXIT_SESSION_STATE
    return 1


def _request_timeout_seconds(wait_timeout_ms):
    return (max(wait_timeout_ms, 1) / 1000.0) + HTTP_TIMEOUT_BUFFER_SECONDS


def _build_exec_payload(args):
    return {
        "id": uuid.uuid4().hex,
        "code": args.code,
        "wait_timeout_ms": args.wait_timeout_ms,
    }


def _build_get_result_payload(args):
    return {
        "job_id": args.job_id,
        "wait_timeout_ms": args.wait_timeout_ms,
    }


def invoke_command(command, base_url, payload, wait_timeout_ms, transport=None):
    transport = transport or HttpTransport()

    try:
        response = transport.post_json(
            base_url.rstrip("/") + "/" + command,
            payload,
            _request_timeout_seconds(wait_timeout_ms),
        )
    except urllib.error.URLError as exc:
        error_payload = {
            "ok": False,
            "status": "not_available",
            "error": str(exc.reason),
        }
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""
    except socket.timeout:
        error_payload = {
            "ok": False,
            "status": "not_available",
            "error": "timed out",
        }
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""

    exit_code = _status_to_exit_code(response)
    if exit_code in (0, EXIT_RUNNING, EXIT_COMPILING, EXIT_NOT_AVAILABLE, EXIT_MISSING, EXIT_SESSION_STATE):
        return exit_code, json.dumps(response, ensure_ascii=True), ""
    return exit_code, "", json.dumps(response, ensure_ascii=True)


def run_cli(argv, transport=None):
    parser = argparse.ArgumentParser(prog="unity-puer-exec")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    subparsers = parser.add_subparsers(dest="command", required=True)

    exec_parser = subparsers.add_parser("exec")
    exec_parser.add_argument("--base-url", default=None)
    exec_parser.add_argument("--code", required=True)
    exec_parser.add_argument("--wait-timeout-ms", type=int, default=DEFAULT_WAIT_TIMEOUT_MS)

    get_result_parser = subparsers.add_parser("get-result")
    get_result_parser.add_argument("--base-url", default=None)
    get_result_parser.add_argument("--job-id", required=True)
    get_result_parser.add_argument("--wait-timeout-ms", type=int, default=DEFAULT_WAIT_TIMEOUT_MS)

    args = parser.parse_args(argv)
    base_url = (args.base_url or DEFAULT_BASE_URL).rstrip("/")

    if args.command == "exec":
        payload = _build_exec_payload(args)
        return invoke_command("exec", base_url, payload, args.wait_timeout_ms, transport=transport)

    payload = _build_get_result_payload(args)
    return invoke_command("get-result", base_url, payload, args.wait_timeout_ms, transport=transport)


def main():
    exit_code, stdout_text, stderr_text = run_cli(sys.argv[1:])
    if stdout_text:
        print(stdout_text)
    if stderr_text:
        print(stderr_text, file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
