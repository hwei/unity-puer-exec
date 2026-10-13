"""Deterministic reproduction for the play-path transport reset flake.

Observed real-host failure (transcript `.tmp/realhost_rest_run.log`, archived change
`2026-10-13-validate-real-host-refresh-trigger-extension`):

    AssertionError: 1 != 0 : {'ok': False, 'status': 'failed', 'operation': 'play',
      'error': '[WinError 10054] ...', 'cli_version': '0.9.0'}

Claim under test: the CLI cannot retry this failure, because the transport exception
class raised by CPython for this edge is not caught by `direct_exec_client.invoke_command`,
so it escapes `_post_play_mode` entirely and is normalized by the top-level envelope to
`status: "failed"` / exit 1 instead of a retryable transport drop.

Run: python repro_play_transport_reset.py

Read-only: it monkeypatches the transport in-process and changes no file and no
product code. Its output is committed alongside it as `repro_play_transport_reset.log`.
"""
import http.client
import json
import socket
import sys
import urllib.error
from pathlib import Path

# Walk up to the repository root so the script runs from any location, including
# from its own tracked copy inside an OpenSpec change directory.
_ROOT = Path(__file__).resolve()
for _parent in _ROOT.parents:
    if (_parent / "cli" / "python" / "direct_exec_client.py").is_file():
        ROOT = _parent
        break
else:  # pragma: no cover - only if the script is copied outside the repository.
    raise SystemExit("cannot locate the unity-puer-exec repository root")
sys.path.insert(0, str(ROOT / "cli" / "python"))

import direct_exec_client  # noqa: E402
import unity_puer_exec_runtime as runtime  # noqa: E402
import unity_puer_exec_surface as surface  # noqa: E402

RESET_TEXT = "remote host forcibly closed an existing connection"


def _peer_reset():
    """The exception CPython actually raises when a peer resets a keep-alive socket.

    `http.client.HTTPConnection.getresponse` raises `RemoteDisconnected` when the
    response status line is empty. On Windows that instance is constructed with the
    `ConnectionResetError(10054, ...)` that came from the socket read, which is what
    produces the `[WinError 10054] ...` text in the observed payload.
    """
    return http.client.RemoteDisconnected(ConnectionResetError(10054, RESET_TEXT))


class RaisingTransport(direct_exec_client.HttpTransport):
    def __init__(self, exc):
        self._exc = exc

    def post_json(self, url, payload, timeout_seconds):
        raise self._exc


print("== 1. Which exceptions does invoke_command() convert to a retryable status? ==")
print("   (a retryable status is what makes _post_play_mode re-resolve and retry)\n")

cases = [
    ("urllib URLError", urllib.error.URLError(ConnectionResetError(10054, RESET_TEXT))),
    ("RemoteDisconnected", _peer_reset()),
    ("ConnectionResetError", ConnectionResetError(10054, RESET_TEXT)),
    ("socket.timeout", socket.timeout()),
    ("ValueError (bad body)", ValueError("truncated body")),
]

verdicts = {}
for label, exc in cases:
    try:
        code, out, _err = direct_exec_client.invoke_command(
            "play-mode", "http://127.0.0.1:59999", {"action": "play"}, 5000,
            transport=RaisingTransport(exc),
        )
    except Exception as escaped:  # noqa: BLE001 - the probe reports what escapes
        print(f"  {label:<22} ESCAPED {type(escaped).__name__} -> NOT retryable")
        verdicts[label] = "escaped"
        continue
    body = json.loads(out) if out else {}
    status = body.get("status")
    retryable = status in (direct_exec_client.STATUS_EMPTY_RESPONSE, "not_available")
    verdicts[label] = "retryable" if retryable else "terminal"
    print(f"  {label:<22} status={status!r:<18} retryable={retryable}")

print("\n== 2. Does the escaped exception reach the observed payload shape? ==")


def _fake_invoke(command, base_url, payload, wait_ms, transport=None):
    if command == "play-mode":
        raise _peer_reset()
    return 0, json.dumps({"ok": True, "status": "ready", "play_state": "edit"}), ""


runtime.direct_exec_client.invoke_command = _fake_invoke
runtime._play_pre_settle = lambda *a, **k: (None, "http://127.0.0.1:59999", None, None)
runtime._play_probe_endpoint = lambda *a, **k: ("edit", None, "http://127.0.0.1:59999")

code, out, _err = runtime.run_cli(
    ["play", "--base-url", "http://127.0.0.1:59999", "--timeout-seconds", "30"], surface
)
print(f"  exit_code: {code}")
print(f"  stdout:    {out.strip()}")

observed = {
    "ok": False, "status": "failed", "operation": "play",
    "error": f"[WinError 10054] {RESET_TEXT}", "cli_version": "0.9.0",
}
produced = json.loads(out)
shape_matches = all(produced.get(k) == v for k, v in observed.items() if k != "error")
print(f"\n  matches the observed real-host envelope shape: {shape_matches}")
print("  (this change does not fix it; see the recorded finding)")