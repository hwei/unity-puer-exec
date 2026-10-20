import http.client
import io
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import direct_exec_client  # type: ignore


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def post_json(self, url, payload, timeout_seconds):
        self.calls.append((url, payload, timeout_seconds))
        return self.responses.pop(0)


class TimeoutTransport:
    def post_json(self, url, payload, timeout_seconds):
        raise socket.timeout()


class MalformedBodyTransport:
    """Mimics the real transport parsing an empty or truncated HTTP body."""

    def post_json(self, url, payload, timeout_seconds):
        raise json.JSONDecodeError("Expecting value", "", 0)


class NonJsonBodyTransport:
    """The endpoint answered with a present-but-not-JSON body."""

    def post_json(self, url, payload, timeout_seconds):
        raise json.JSONDecodeError("Expecting value", "<html>not json</html>", 0)


class InvalidUtf8BodyTransport:
    """The endpoint answered with bytes that are not valid UTF-8."""

    def post_json(self, url, payload, timeout_seconds):
        raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")


class RaisingTransport:
    def __init__(self, exc):
        self.exc = exc

    def post_json(self, url, payload, timeout_seconds):
        raise self.exc


class HttpErrorTransport:
    """Raises the `HTTPError` the real transport raises for a non-2xx answer.

    `HTTPError` is itself the readable response, so the CLI can still inspect the
    body the service wrote alongside its status code.
    """

    def __init__(self, code, body=b"", message="error"):
        self.code = code
        self.body = body
        self.message = message
        self.calls = []

    def post_json(self, url, payload, timeout_seconds):
        self.calls.append((url, payload, timeout_seconds))
        raise urllib.error.HTTPError(url, self.code, self.message, {}, io.BytesIO(self.body))


class _UnreadableBody:
    def read(self, *_args):
        raise OSError("connection lost while reading the error body")


class UnreadableHttpErrorTransport:
    """An `HTTPError` whose body cannot be read at all."""

    def post_json(self, url, payload, timeout_seconds):
        raise urllib.error.HTTPError(url, 500, "error", {}, _UnreadableBody())


def peer_reset_exception():
    """The exception CPython raises when a peer resets a keep-alive socket.

    `RemoteDisconnected` is constructed with the `ConnectionResetError` that came
    from the socket read, which is what carries the `[WinError 10054]` text.
    """
    return http.client.RemoteDisconnected(
        ConnectionResetError(10054, "remote host forcibly closed an existing connection")
    )


class DirectExecClientTests(unittest.TestCase):
    def test_http_transport_disables_proxy_for_localhost(self):
        response = mock.Mock()
        response.read.return_value = b'{"ok": true, "status": "ready"}'
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        opener = mock.Mock()
        opener.open.return_value = response

        with mock.patch.object(urllib.request, "build_opener", return_value=opener) as build_opener:
            transport = direct_exec_client.HttpTransport()
            payload = transport.post_json(
                "http://127.0.0.1:55231/health",
                {"ping": True},
                1.0,
            )

        self.assertEqual(payload["status"], "ready")
        proxy_handler = build_opener.call_args[0][0]
        self.assertIsInstance(proxy_handler, urllib.request.ProxyHandler)
        self.assertEqual(proxy_handler.proxies, {})

    def test_request_timeout_adds_http_buffer(self):
        self.assertEqual(
            direct_exec_client._request_timeout_seconds(1500),
            6.5,
        )

    def test_invoke_command_completed_payload_stays_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": True,
                "status": "completed",
                "log_offset": 12345,
                "result": {"value": 2},
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {
                "request_id": "req-1",
                "code": "export default function run(ctx) { return 1 + 1; }",
                "wait_timeout_ms": 1500,
            },
            1500,
            transport=transport,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            transport.calls,
            [
                (
                    "http://127.0.0.1:55231/exec",
                    {
                        "request_id": "req-1",
                        "code": "export default function run(ctx) { return 1 + 1; }",
                        "wait_timeout_ms": 1500,
                    },
                    6.5,
                )
            ],
        )
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["log_offset"], 12345)

    def test_invoke_command_running_returns_dedicated_exit_code(self):
        transport = FakeTransport([
            {
                "ok": True,
                "status": "running",
                "log_offset": 678,
                "result": {"correlation_id": "id-9"},
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {
                "request_id": "req-2",
                "code": "export default function run(ctx) { return { phase: 'started' }; }",
                "wait_timeout_ms": 1000,
            },
            1000,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["log_offset"], 678)
        self.assertEqual(body["result"]["correlation_id"], "id-9")

    def test_session_state_payloads_stay_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "session_stale",
                "error": "marker changed",
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "wait-for-result-marker",
            "http://127.0.0.1:55231",
            {"correlation_id": "id-2"},
            800,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_SESSION_STATE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "session_stale")

    def test_missing_payload_is_non_zero(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "missing",
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "wait-for-log-pattern",
            "http://127.0.0.1:55231",
            {"pattern": "x"},
            800,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_MISSING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "missing")

    def test_failed_response_goes_to_stderr(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "failed",
                "error": "boom",
                "stack": "stack-text",
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {
                "request_id": "req-3",
                "code": "throw new Error('boom')",
                "wait_timeout_ms": 1000,
            },
            1000,
            transport=transport,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["error"], "boom")

    def test_socket_timeout_returns_not_available_payload(self):
        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {
                "request_id": "req-4",
                "code": "export default function run(ctx) { return 1; }",
                "wait_timeout_ms": 1000,
            },
            1000,
            transport=TimeoutTransport(),
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "not_available")
        self.assertEqual(body["error"], "timed out")
        self.assertEqual(body["request_id"], "req-4")

    def test_malformed_response_body_is_a_named_empty_response_state(self):
        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "refresh",
            "http://127.0.0.1:55231",
            {"request_id": "req-empty"},
            1000,
            transport=MalformedBodyTransport(),
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], direct_exec_client.STATUS_EMPTY_RESPONSE)
        self.assertEqual(body["operation"], "refresh")
        self.assertEqual(body["request_id"], "req-empty")
        # The interpreter text is quarantined, never the caller-facing error.
        self.assertNotIn("Expecting value", body["error"])
        self.assertIn("Expecting value", body["response_detail"]["decode_error"])
        self.assertEqual(body["exit_code"], direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertIn("endpoint", body["exit_code_meaning"])
        self.assertTrue(body["next_steps"], "empty_response must carry a continuation")

    def test_empty_or_unparseable_body_is_named_for_every_command_family(self):
        # The decode boundary is shared, so no command family may surface the
        # interpreter text or a bare not_available for the same condition.
        families = (
            "exec",
            "wait-for-exec",
            "refresh",
            "reset-jsenv",
            "play-mode",
            "get-compile-errors",
            "get-compile-warnings",
            "get-log-source",
            "get-log-briefs",
            "get-blocker-state",
            "resolve-blocker",
        )
        for command in families:
            for transport in (MalformedBodyTransport(), NonJsonBodyTransport(), InvalidUtf8BodyTransport()):
                with self.subTest(command=command, transport=type(transport).__name__):
                    exit_code, stdout, stderr = direct_exec_client.invoke_command(
                        command,
                        "http://127.0.0.1:55231",
                        {"request_id": "req-empty"},
                        1000,
                        transport=transport,
                    )
                    self.assertEqual(stderr, "")
                    body = json.loads(stdout)
                    self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
                    self.assertEqual(body["status"], direct_exec_client.STATUS_EMPTY_RESPONSE)
                    self.assertEqual(body["operation"], command)
                    self.assertNotIn("Expecting value", body["error"])
                    self.assertTrue(body["next_steps"])

    def test_unexpected_transport_error_is_not_collapsed_into_empty_response(self):
        class UnexpectedFailureTransport:
            def post_json(self, url, payload, timeout_seconds):
                raise RuntimeError("unexpected boom")

        # A non-ValueError transport failure is not swallowed into empty_response;
        # only an undecodable body is. This keeps the new state narrow so the
        # runtime's generic handler can still report a distinct failed/exit-1.
        with self.assertRaises(RuntimeError):
            direct_exec_client.invoke_command(
                "exec",
                "http://127.0.0.1:55231",
                {"request_id": "req-boom"},
                1000,
                transport=UnexpectedFailureTransport(),
            )

    def test_peer_reset_is_classified_as_a_retryable_transport_drop(self):
        # A peer reset matches none of the narrower handlers, so it used to escape
        # `invoke_command` and reach the top-level envelope as status "failed" / exit 1,
        # which put `_post_play_mode`'s retry branch out of reach entirely.
        code, out, _err = direct_exec_client.invoke_command(
            "play-mode",
            "http://127.0.0.1:55231",
            {"action": "play", "request_id": "req-reset"},
            1000,
            transport=RaisingTransport(peer_reset_exception()),
        )
        body = json.loads(out)
        self.assertEqual(code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(body["status"], "not_available")
        self.assertEqual(body["operation"], "play-mode")
        self.assertEqual(body["request_id"], "req-reset")
        # The reset errno must stay visible so a recurrence is recognizable.
        self.assertIn("10054", body["error"])
        self.assertEqual(body["transport_detail"]["reason"], "RemoteDisconnected")

    def test_peer_reset_siblings_map_to_not_available(self):
        # `OSError` is a broad base, so each condition the widened catch admits is
        # asserted rather than assumed. All of them mean "the endpoint is not
        # answering", which is what `not_available` denotes.
        cases = [
            (http.client.BadStatusLine("garbage status line"), "BadStatusLine", "garbage status line"),
            (ConnectionRefusedError(10061, "connection refused"), "ConnectionRefusedError", "10061"),
            (ConnectionAbortedError(10053, "software caused connection abort"), "ConnectionAbortedError", "10053"),
            (ConnectionResetError(10054, "connection reset by peer"), "ConnectionResetError", "10054"),
        ]
        for exc, reason, text in cases:
            with self.subTest(reason=reason):
                code, out, _err = direct_exec_client.invoke_command(
                    "play-mode",
                    "http://127.0.0.1:55231",
                    {"action": "play"},
                    1000,
                    transport=RaisingTransport(exc),
                )
                body = json.loads(out)
                self.assertEqual(code, direct_exec_client.EXIT_NOT_AVAILABLE)
                self.assertEqual(body["status"], "not_available")
                self.assertIn(text, body["error"])
                self.assertEqual(body["transport_detail"]["reason"], reason)

    def test_unrelated_exceptions_still_escape_the_boundary(self):
        # Widening to OSError/HTTPException must not swallow programming errors.
        with self.assertRaises(RuntimeError):
            direct_exec_client.invoke_command(
                "exec",
                "http://127.0.0.1:55231",
                {},
                1000,
                transport=RaisingTransport(RuntimeError("unexpected boom")),
            )

    def test_busy_payload_is_non_zero_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "busy",
                "request_id": "req-5",
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {"request_id": "req-5", "code": "export default function run(ctx) { return 1; }", "wait_timeout_ms": 500},
            500,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_BUSY)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "busy")
        self.assertEqual(body["request_id"], "req-5")

    def test_request_id_conflict_payload_is_non_zero_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "request_id_conflict",
                "request_id": "req-6",
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {"request_id": "req-6", "code": "export default function run(ctx) { return 1; }", "wait_timeout_ms": 500},
            500,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_REQUEST_ID_CONFLICT)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "request_id_conflict")
        self.assertEqual(body["request_id"], "req-6")

    def test_modal_blocked_payload_is_non_zero_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "modal_blocked",
                "request_id": "req-7",
                "blocker": {"type": "save_scene_dialog", "scope": "exec"},
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "wait-for-exec",
            "http://127.0.0.1:55231",
            {"request_id": "req-7"},
            500,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_MODAL_BLOCKED)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "modal_blocked")
        self.assertEqual(body["blocker"]["type"], "save_scene_dialog")

    def test_compile_error_status_maps_to_exit_code(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "unity_compile_error",
                "request_id": "req-ce",
                "compile_errors_total": 3,
                "compile_warnings_total": 0,
                "compile_messages": ["error1", "error2"],
            }
        ])

        exit_code, stdout, stderr = direct_exec_client.invoke_command(
            "exec",
            "http://127.0.0.1:55231",
            {"request_id": "req-ce", "code": "export default function(ctx) {}", "wait_timeout_ms": 1000},
            500,
            transport=transport,
        )

        self.assertEqual(exit_code, direct_exec_client.EXIT_UNITY_COMPILE_ERROR)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "unity_compile_error")
        self.assertEqual(body["compile_errors_total"], 3)
        self.assertEqual(body["compile_warnings_total"], 0)


class ServiceInternalClassificationTests(unittest.TestCase):
    """`failure_origin: service_internal` only for the service's own 500 body."""

    BASE_URL = "http://127.0.0.1:55231"
    INTERNAL_BODY = b'{"ok": false, "status": "failed", "error": "internal_error"}'

    def _invoke(self, transport):
        return direct_exec_client.invoke_command(
            "exec",
            self.BASE_URL,
            {"request_id": "req-500", "code": "export default function(ctx) {}"},
            1000,
            transport=transport,
        )

    def test_http_500_with_internal_error_body_is_marked_without_changing_status(self):
        exit_code, stdout, stderr = self._invoke(HttpErrorTransport(500, self.INTERNAL_BODY))

        self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["failure_origin"], "service_internal")
        # The field is additive: the pre-existing HTTP 500 reporting is untouched.
        self.assertEqual(body["status"], "not_available")
        self.assertEqual(body["http_status"], 500)
        self.assertEqual(body["request_id"], "req-500")

    def test_http_500_without_a_usable_body_is_not_marked(self):
        cases = {
            "empty": b"",
            "not_json": b"<html>Internal Server Error</html>",
            "not_an_object": b"[1, 2, 3]",
            "other_error": b'{"ok": false, "status": "failed", "error": "script_error"}',
        }
        for label, payload in cases.items():
            with self.subTest(label):
                exit_code, stdout, _stderr = self._invoke(HttpErrorTransport(500, payload))
                self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
                body = json.loads(stdout)
                self.assertEqual(body["status"], "not_available")
                self.assertNotIn("failure_origin", body)

    def test_other_http_statuses_are_not_marked(self):
        for code in (404, 400, 503):
            with self.subTest(code):
                exit_code, stdout, _stderr = self._invoke(HttpErrorTransport(code, self.INTERNAL_BODY))
                self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
                body = json.loads(stdout)
                self.assertEqual(body["http_status"], code)
                self.assertNotIn("failure_origin", body)

    def test_an_unreadable_error_body_still_degrades_to_the_plain_payload(self):
        exit_code, stdout, stderr = self._invoke(UnreadableHttpErrorTransport())

        self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "not_available")
        self.assertEqual(body["http_status"], 500)
        self.assertNotIn("failure_origin", body)


if __name__ == "__main__":
    unittest.main()
