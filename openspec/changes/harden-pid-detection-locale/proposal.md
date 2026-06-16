## Why

`cli/python/unity_session_process.py::is_pid_running` decides whether a recorded
Unity PID is still alive by running `tasklist /FI "PID eq <pid>"` and checking the
output only for the **English** sentinel `"No tasks are running"`. On a localized
Windows host (e.g. Chinese), `tasklist` emits a localized "no tasks" line that
never matches that sentinel, so `is_pid_running` returns `True` for *any* PID —
including dead ones.

This surfaced during apply of `cover-port-binding-real-host-regression` on a
Chinese Windows host: after a real-host test teardown kills its Editor, the stale
`Temp/UnityPuerExec/session.json` still records the now-dead Editor PID. The next
test's `_ensure_clean_test_boundary` believes that dead PID is alive, runs
`taskkill` (which reports "process not found", exit 128), and `ensure-stopped`
returns `not_stopped`. The net effect: any two real-host tests run in sequence
fail on a non-English Windows host, and `ensure-stopped` in project-path mode can
falsely report a dead session as still running in normal operation too.

`list_unity_pids` in the same module is already locale-robust because it parses
the CSV `Unity.exe` rows rather than matching an English sentence. `is_pid_running`
should be hardened the same way.

## What Changes

- Rewrite `is_pid_running` to determine liveness from the parsed `tasklist` CSV
  (PID row present) rather than from the absence of an English "no tasks" string,
  so detection is independent of the OS display language.
- Add a unit test that proves locale-independence by feeding both English and
  localized "no tasks" `tasklist` outputs through the parsing path (no real
  process dependency), plus the positive (PID present) case.
- No behavior change on English hosts; this only removes the false-positive
  liveness on localized hosts.

## Capabilities

### New Capabilities
<!-- None: this corrects an existing CLI contract behavior. -->

### Modified Capabilities

- `formal-cli-contract`: Strengthen the `ensure-stopped` contract so that process
  liveness detection is locale-independent — `ensure-stopped` reports `stopped`
  when the recorded session PID is no longer running, regardless of the host's
  display language.

## Impact

- Code: `cli/python/unity_session_process.py` (`is_pid_running`).
- Tests: `tests/test_unity_session_modules.py` (or the nearest process-module unit
  test) — add locale-independence coverage.
- Spec: `openspec/specs/formal-cli-contract/spec.md` — one modified requirement.
- Unblocks reliable sequential real-host runs of `tests/test_real_host_integration`
  on non-English Windows hosts (regression coverage added in
  `cover-port-binding-real-host-regression`).
