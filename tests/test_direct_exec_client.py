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


if __name__ == "__main__":
    unittest.main()
