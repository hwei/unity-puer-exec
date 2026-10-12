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
EXIT_MODAL_BLOCKED = 19
EXIT_MODULE_CACHE_STALE = 22
EXIT_UNITY_COMPILE_ERROR = 23
EXIT_VERSION_MISMATCH = 24

# Named non-success state for a control-endpoint response whose body is empty or
# cannot be parsed as JSON. `json.loads("")` is the common case (the endpoint
# dropped mid-domain-reload after accepting the request); invalid UTF-8 is the
# other. It is deliberately distinct from `not_available`: an unreachable target
# and an answered-but-empty body are different conditions, even though they share
# exit code 12 so the baseline exit-code model is unchanged.
STATUS_EMPTY_RESPONSE = "empty_response"
EMPTY_RESPONSE_ERROR = (
    "The control endpoint returned an empty or unparseable response body; "
    "the response could not be decoded as JSON."
)
EMPTY_RESPONSE_EXIT_MEANING = "the control endpoint answered without a usable response body"

# Control-port range contract. The Unity control service binds the preferred port
# first and rolls over to later ports in [CONTROL_PORT_PREFERRED, CONTROL_PORT_END)
# when the preferred port is occupied, so multiple Editors can run concurrently.
# The CLI mirrors this same range when discovering a project's live endpoint.
#
# These three values MUST equal PreferredPort and MaxPortAttempts in
# packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs, which binds
# `for (port = PreferredPort; port < PreferredPort + MaxPortAttempts; port++)`.
# An earlier 55250 exclusive bound silently omitted 55250 -- the last port the
# service can bind -- so an Editor there was invisible to range-scan discovery.
# tests/test_package_layout.py pins the equality against the package source.
CONTROL_PORT_HOST = "127.0.0.1"
CONTROL_PORT_PREFERRED = 55231
CONTROL_PORT_END = 55251  # exclusive upper bound: ports [55231, 55251) == [55231, 55250]
CONTROL_PORT_COUNT = CONTROL_PORT_END - CONTROL_PORT_PREFERRED


def base_url_for_port(port):
    return "http://{}:{}".format(CONTROL_PORT_HOST, port)


def control_port_candidates():
    """Control ports in preferred-first order."""
    return list(range(CONTROL_PORT_PREFERRED, CONTROL_PORT_END))


def candidate_base_urls():
    """Loopback control-endpoint base URLs in preferred-first order."""
    return [base_url_for_port(port) for port in control_port_candidates()]


DEFAULT_BASE_URL = base_url_for_port(CONTROL_PORT_PREFERRED)
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


def status_to_exit_code(payload):
    """Map a control-endpoint payload to its formal process exit code.

    This is the single source of truth for the status→exit-code contract shared
    by the transport boundary and the command envelopes that re-wrap a body.
    """
    if payload.get("ok"):
        if payload.get("status") == "running":
            return EXIT_RUNNING
        return 0

    status = payload.get("status")
    if status == "compiling":
        return EXIT_COMPILING
    if status in ("not_available", STATUS_EMPTY_RESPONSE):
        return EXIT_NOT_AVAILABLE
    if status == "missing":
        return EXIT_MISSING
    if status == "busy":
        return EXIT_BUSY
    if status == "request_id_conflict":
        return EXIT_REQUEST_ID_CONFLICT
    if status == "modal_blocked":
        return EXIT_MODAL_BLOCKED
    if status == "module_cache_stale":
        return EXIT_MODULE_CACHE_STALE
    if status == "unity_compile_error":
        return EXIT_UNITY_COMPILE_ERROR
    if status == "version_mismatch":
        return EXIT_VERSION_MISMATCH
    if status in ("session_missing", "session_stale"):
        return EXIT_SESSION_STATE
    return 1


def _status_to_exit_code(payload):
    """Backward-compatible private alias for :func:`status_to_exit_code`."""
    return status_to_exit_code(payload)


def _request_timeout_seconds(wait_timeout_ms):
    return (max(wait_timeout_ms, 1) / 1000.0) + HTTP_TIMEOUT_BUFFER_SECONDS


def _payload_request_id(payload):
    if not isinstance(payload, dict):
        return None
    return payload.get("request_id") or payload.get("id")


def _empty_response_payload(command, exc, request_id=None):
    """Structured, branchable payload for an empty/unparseable response body.

    The raw interpreter text is quarantined under `response_detail.decode_error`
    instead of `error`, so the caller-facing `error` describes the condition.
    """
    payload = {
        "ok": False,
        "status": STATUS_EMPTY_RESPONSE,
        "operation": command,
        "error": EMPTY_RESPONSE_ERROR,
        "response_detail": {"reason": STATUS_EMPTY_RESPONSE, "decode_error": str(exc)},
        "exit_code": EXIT_NOT_AVAILABLE,
        "exit_code_meaning": EMPTY_RESPONSE_EXIT_MEANING,
        "next_steps": [
            {
                "command": command,
                "when": (
                    "the endpoint may have dropped during a domain reload; retry once "
                    "the Editor reports ready again"
                ),
            }
        ],
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def invoke_command(command, base_url, payload, wait_timeout_ms, transport=None):
    transport = transport or HttpTransport()
    request_id = _payload_request_id(payload)

    try:
        response = transport.post_json(
            base_url.rstrip("/") + "/" + command,
            payload,
            _request_timeout_seconds(wait_timeout_ms),
        )
    except urllib.error.HTTPError as exc:
        # An HTTP status is a transport-level response, not an unreachable target.
        # Command callers distinguish an endpoint that answered 404 (an older package
        # missing the route) from one that never answered.
        error_payload = {
            "ok": False,
            "status": "not_available",
            "error": str(exc),
            "http_status": exc.code,
        }
        if request_id:
            error_payload["request_id"] = request_id
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""
    except urllib.error.URLError as exc:
        error_payload = {
            "ok": False,
            "status": "not_available",
            "error": str(exc.reason),
        }
        if request_id:
            error_payload["request_id"] = request_id
        return EXIT_NOT_AVAILABLE, json.dumps(error_payload, ensure_ascii=True), ""
    except ValueError as exc:
        # A truncated, empty, or non-UTF-8 body is a response condition, not a
        # command failure: name it so the caller can branch instead of parsing the
        # interpreter's exception text.
        error_payload = _empty_response_payload(command, exc, request_id=request_id)
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

    exit_code = status_to_exit_code(response)
    if exit_code in (
        0,
        EXIT_RUNNING,
        EXIT_COMPILING,
        EXIT_NOT_AVAILABLE,
        EXIT_MISSING,
        EXIT_SESSION_STATE,
        EXIT_BUSY,
        EXIT_REQUEST_ID_CONFLICT,
        EXIT_MODAL_BLOCKED,
        EXIT_MODULE_CACHE_STALE,
        EXIT_UNITY_COMPILE_ERROR,
        EXIT_VERSION_MISMATCH,
    ):
        return exit_code, json.dumps(response, ensure_ascii=True), ""
    return exit_code, "", json.dumps(response, ensure_ascii=True)
