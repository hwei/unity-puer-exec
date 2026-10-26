# Proposal

## Why

`unity-puer-exec ensure-closed` crashed on a zh-CN Windows host, after it had already killed the Editor:

```
Thread-1 ... UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb4 in position 0
{"ok": false, "status": "failed", "operation": "ensure-closed",
 "error": "'NoneType' object has no attribute 'strip'", "failure_origin": "cli_internal"}
```

Root cause (reproduced deterministically):

- The interpreter runs in UTF-8 mode (`PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`), so `subprocess.run(..., universal_newlines=True)` decodes the child's output as UTF-8.
- `taskkill` and `tasklist` write their messages in the console code page (cp936 here), which is not valid UTF-8.
- The reader thread raises `UnicodeDecodeError`, and `subprocess` leaves that stream as `None`.
- `unity_session_process.py` then calls `.strip()` on it (twice), so the command dies with `AttributeError`.

Two properties make this worse than a cosmetic decode error:

- The kill has already happened when the crash occurs, so the caller sees `ok: false` for a stop that did succeed — and cannot tell that from a stop that did not.
- The same failure silently empties stream-based helpers: `is_pid_running` and `list_unity_pids` get `stdout = None` and report "not running" / "no Editors". Those answers happen to be right for ASCII rows and for the localized no-match message, so the bug is invisible there until it isn't.

This is not a zh-CN-only defect: it fires whenever the host tool's output is not valid UTF-8 while the interpreter decodes as UTF-8, which is any non-English Windows console code page under UTF-8 mode.

## What Changes

- Host-tool invocations (`tasklist`, `taskkill`) decode with replacement instead of raising, so a stream is never `None` and undecodable bytes degrade to `�` in diagnostic text only.
- Diagnostics that echo that text are `None`-safe, so a missing stream can never fail the command.
- Process-state decisions keep parsing the CSV/exit code, not the message text; the existing requirement that liveness detection is display-language independent is unchanged and this change makes the command survive the same condition.
- Regression tests pin the failure mode by simulating the exact post-failure shape (`stdout`/`stderr` = `None`) rather than depending on a localized host.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `formal-cli-contract`: adds a requirement that decoding host-tool output cannot fail a command, and that an unreadable stream degrades to empty diagnostics rather than a crash.

## Impact

- CLI: `cli/python/unity_session_process.py` (one decode helper used by the four `subprocess.run` call sites, `None`-safe diagnostics).
- Tests: `tests/test_unity_session.py`, `tests/test_unity_session_modules.py` (simulated `None` streams, decode kwargs).
- Compatibility: none for callers. Exit codes and statuses are unchanged for every case that did not crash; the crashing case now reports the outcome it actually produced.
