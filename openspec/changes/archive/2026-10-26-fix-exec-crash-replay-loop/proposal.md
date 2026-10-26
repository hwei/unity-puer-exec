# Proposal

## Why

GitHub issue #2: a script that crashes the Unity Editor natively is re-executed after every Editor relaunch, so one `exec` produced 5 crashes in ~11 minutes. The caller only ever saw `not_available` / `timed out`, so the crash was masked instead of reported.

Root cause (observed in code):

- Project-scoped `exec` writes a pending-exec artifact holding the full script before submitting. When the submit ends in `not_available` (the connection dies with the Editor), the artifact is kept as recoverable.
- `wait-for-exec` with a pending artifact relaunches Unity through `ensure_session_ready` and then **resubmits the whole script** as an `exec` under the same `request_id`.
- Server-side job records live only in memory, so the new Editor treats the replay as a new request (`new=True`), runs it, and crashes again. The loop ends only when the pending artifact expires.

The request-identity contract (`request_id` replays "without duplicate execution") only holds within one Editor process. Exec scripts are not idempotent (this one reimported assets), so re-running them after a crash is wrong in its own right.

## What Changes

- The Unity-side service writes a per-request **start journal** entry to disk right before it hands a script to the JS engine, and removes it when the job reaches a terminal state. An entry that outlives its Editor process is proof that the process died mid-script.
- A service instance that receives `exec` or `wait-for-exec` for a `request_id` whose journal entry belongs to a different (dead) Editor process does **not** run the script. It answers with a new terminal status `editor_crashed_during_request`. This guard works for both selectors.
- Project-scoped `exec` and `wait-for-exec` read the journal before replaying or relaunching. When the recorded Editor process is gone, the CLI reports `editor_crashed_during_request` **without relaunching Unity** and without replaying the pending artifact, so the crashed Editor's log is kept as it was rather than overwritten by a new launch.
- The crash response carries evidence for the caller: Editor pid, start time, the Editor log path, the Unity crash report directory when one is found, `resubmit_safe: false`, a `situation` that says the script most likely crashed the Editor, and `next_steps`. It has its own exit code (26).
- Help for `exec` and `wait-for-exec` lists the new status. The README scripting notes record the known PuerTS native crash (passing `null` for a C# `out` parameter; use `puer.$ref()`).

Not changed: the replay path for requests that never started (startup not ready, refreshing, compiling) keeps working, since no journal entry exists for them.

## Capabilities

### New Capabilities

- `editor-crash-surface`: detecting that the Editor process died while an accepted exec script was running, refusing to re-execute that request, and reporting the crash as a distinct terminal outcome with evidence.

### Modified Capabilities

- None. The new `exec` / `wait-for-exec` help statuses are specified as ADDED requirements in `editor-crash-surface`, so no existing `formal-cli-contract` requirement text changes.

## Impact

- Unity package: `UnityPuerExecServer.cs` (journal write before `ExecuteModule`, removal in the terminal path, guard in the exec accept and wait-for-exec paths), `UnityPuerExecProtocol.cs` (crash response JSON), and a new small journal helper.
- CLI: `unity_puer_exec_runtime.py` (journal check in `exec` / `wait-for-exec`, crash payload), `unity_session_logs.py` / `unity_session_common.py` (journal path, read, sweep), `help_surface.py` (status tables, guidance matrix, exit code 26), `unity_puer_exec_surface.py` / exit constants.
- Docs: `README.md`, `README.zh-CN.md`, package README scripting notes.
- Tests: `tests/test_unity_session_cli.py`, `tests/test_unity_session_modules.py`, EditMode tests for the journal, and one real-host regression that crashes the Editor on purpose.
- Compatibility: a new CLI against an old package has no journal, so the CLI falls back to current behavior. An old CLI against a new package still gets the server-side guard (no re-execution); it sees the new status as an unknown failure.
