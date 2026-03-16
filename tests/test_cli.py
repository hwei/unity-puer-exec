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

import cli  # type: ignore


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


class CliTests(unittest.TestCase):
    def test_http_transport_disables_proxy_for_localhost(self):
        response = mock.Mock()
        response.read.return_value = b'{"ok": true, "status": "ready"}'
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        opener = mock.Mock()
        opener.open.return_value = response

        with mock.patch.object(urllib.request, "build_opener", return_value=opener) as build_opener:
            transport = cli.HttpTransport()
            payload = transport.post_json(
                "http://127.0.0.1:55231/health",
                {"ping": True},
                1.0,
            )

        self.assertEqual(payload["status"], "ready")
        proxy_handler = build_opener.call_args[0][0]
        self.assertIsInstance(proxy_handler, urllib.request.ProxyHandler)
        self.assertEqual(proxy_handler.proxies, {})

    def test_exec_completed_prints_current_job_and_spawned_jobs(self):
        transport = FakeTransport([
            {
                "ok": True,
                "status": "completed",
                "job_id": "exec-1",
                "result": {"value": 2},
                "spawn_job_ids": ["job-1", "job-2"],
            }
        ])

        exit_code, stdout, stderr = cli.run_cli(
            [
                "exec",
                "--base-url",
                "http://127.0.0.1:55231",
                "--wait-timeout-ms",
                "1500",
                "--code",
                "return 1 + 1;",
            ],
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
                        "id": mock.ANY,
                        "code": "return 1 + 1;",
                        "wait_timeout_ms": 1500,
                    },
                    6.5,
                )
            ],
        )
        body = json.loads(stdout)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["job_id"], "exec-1")
        self.assertEqual(body["spawn_job_ids"], ["job-1", "job-2"])

    def test_exec_running_returns_dedicated_exit_code(self):
        transport = FakeTransport([
            {
                "ok": True,
                "status": "running",
                "job_id": "exec-2",
                "spawn_job_ids": ["job-9"],
            }
        ])

        exit_code, stdout, stderr = cli.run_cli(
            [
                "exec",
                "--code",
                "await host.delayMs(5000); return 42;",
            ],
            transport=transport,
        )

        self.assertEqual(exit_code, cli.EXIT_RUNNING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["job_id"], "exec-2")
        self.assertEqual(body["spawn_job_ids"], ["job-9"])

    def test_session_state_payloads_stay_on_stdout(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "session_stale",
                "job_id": "job-2",
                "error": "marker changed",
            }
        ])

        exit_code, stdout, stderr = cli.invoke_command(
            "get-result",
            "http://127.0.0.1:55231",
            {"job_id": "job-2", "wait_timeout_ms": 800},
            800,
            transport=transport,
        )

        self.assertEqual(exit_code, cli.EXIT_SESSION_STATE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "session_stale")

    def test_get_result_missing_is_non_zero(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "missing",
                "job_id": "job-missing",
            }
        ])

        exit_code, stdout, stderr = cli.run_cli(
            [
                "get-result",
                "--job-id",
                "job-missing",
                "--wait-timeout-ms",
                "800",
            ],
            transport=transport,
        )

        self.assertEqual(exit_code, cli.EXIT_MISSING)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "missing")
        self.assertEqual(body["job_id"], "job-missing")

    def test_failed_response_goes_to_stderr(self):
        transport = FakeTransport([
            {
                "ok": False,
                "status": "failed",
                "job_id": "exec-err",
                "error": "boom",
                "stack": "stack-text",
            }
        ])

        exit_code, stdout, stderr = cli.run_cli(
            [
                "exec",
                "--code",
                "throw new Error('boom')",
            ],
            transport=transport,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        body = json.loads(stderr)
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["error"], "boom")

    def test_socket_timeout_returns_not_available_payload(self):
        exit_code, stdout, stderr = cli.run_cli(
            [
                "exec",
                "--code",
                "return 1;",
            ],
            transport=TimeoutTransport(),
        )

        self.assertEqual(exit_code, cli.EXIT_NOT_AVAILABLE)
        self.assertEqual(stderr, "")
        body = json.loads(stdout)
        self.assertEqual(body["status"], "not_available")
        self.assertEqual(body["error"], "timed out")


if __name__ == "__main__":
    unittest.main()
