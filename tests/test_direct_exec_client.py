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
                "id": "req-1",
                "code": "return 1 + 1;",
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
                        "id": "req-1",
                        "code": "return 1 + 1;",
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
                "id": "req-2",
                "code": "await host.delayMs(5000); return 42;",
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
                "id": "req-3",
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
                "id": "req-4",
                "code": "return 1;",
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


if __name__ == "__main__":
    unittest.main()
