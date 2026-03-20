#!/usr/bin/env python3
import json
import socket
import urllib.error
import urllib.request


EXIT_RUNNING = 10
EXIT_COMPILING = 11
EXIT_NOT_AVAILABLE = 12
EXIT_MISSING = 13
EXIT_SESSION_STATE = 14
EXIT_BUSY = 17
EXIT_REQUEST_ID_CONFLICT = 18

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
    if status == "busy":
        return EXIT_BUSY
    if status == "request_id_conflict":
        return EXIT_REQUEST_ID_CONFLICT
    if status in ("session_missing", "session_stale"):
        return EXIT_SESSION_STATE
    return 1


def _request_timeout_seconds(wait_timeout_ms):
    return (max(wait_timeout_ms, 1) / 1000.0) + HTTP_TIMEOUT_BUFFER_SECONDS


def _payload_request_id(payload):
    if not isinstance(payload, dict):
        return None
    return payload.get("request_id") or payload.get("id")


def invoke_command(command, base_url, payload, wait_timeout_ms, transport=None):
    transport = transport or HttpTransport()
    request_id = _payload_request_id(payload)

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
        if request_id:
            error_payload["request_id"] = request_id
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""
    except socket.timeout:
        error_payload = {
            "ok": False,
            "status": "not_available",
            "error": "timed out",
        }
        if request_id:
            error_payload["request_id"] = request_id
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""

    exit_code = _status_to_exit_code(response)
    if exit_code in (
        0,
        EXIT_RUNNING,
        EXIT_COMPILING,
        EXIT_NOT_AVAILABLE,
        EXIT_MISSING,
        EXIT_SESSION_STATE,
        EXIT_BUSY,
        EXIT_REQUEST_ID_CONFLICT,
    ):
        return exit_code, json.dumps(response, ensure_ascii=True), ""
    return exit_code, "", json.dumps(response, ensure_ascii=True)
