# Tasks

## 1. Server-side start journal and guard (Unity package)

- [x] 1.1 Add a journal helper (new `UnityPuerExecExecJournal.cs` + `.meta`) with key derivation (`^[A-Za-z0-9._-]{1,128}$`, else SHA-256 hex), atomic write (temp + rename), read, delete, and startup sweep of entries older than 24h or malformed. Verify it compiles in the validation host (`UNITY_PROJECT_PATH`) with no compile errors.
- [x] 1.2 In `StartJobEvaluation`, write the journal entry (`editor_pid`, `process_start_utc`, `started_at_utc`, `editor_log_path`) after the JsEnv/wrapper early-fail checks and right before `jsEnv.ExecuteModule`. In `ReleaseActiveRequest`, delete it. Verify with an EditMode test that a completed or failed job leaves no entry.
- [x] 1.3 Add the `editor_crashed` accept status to `TryAcceptExecRequest` (no in-memory record + entry from a different pid or process start time), plus `UnityPuerExecProtocol.BuildEditorCrashedResponseJson`. Wire it into the exec handler (no enqueue) and into `wait-for-exec` before `missing`. Verify with EditMode tests: a foreign-process entry yields `editor_crashed_during_request`, and a current-process entry or no entry keeps today's behavior.

## 2. CLI journal reading and crash surface

- [x] 2.1 Add journal path, key derivation, read, and sweep helpers next to the pending-exec helpers (`unity_session_common.py`, `unity_session_logs.py`, re-exported through `unity_session.py`). Verify with unit tests in `tests/test_unity_session_modules.py` covering key derivation parity with the C# rule, expired entries, and malformed entries.
- [x] 2.2 Add `EXIT_EDITOR_CRASHED_DURING_REQUEST = 26` and a crash payload builder in `unity_puer_exec_runtime.py`: `editor_pid`, `started_at`, `editor_log_path`, `crash_report_dir` (newest `Crash_*` under `%TEMP%/Unity/Editor/Crashes` with mtime at or after `started_at - 5s`), `log_range`, `resubmit_safe: false`, `recoverable: false`, `situation`. Apply the same enrichment when the server returns `editor_crashed_during_request`. Verify with unit tests that the payload fields are present and that `crash_report_dir` is omitted when no report is found.
- [x] 2.3 In project-mode `wait-for-exec` and `exec`, check the journal before `ensure_session_ready`. A dead-pid entry returns exit 26, clears the pending artifact, and does not launch or resubmit. Verify with tests in `tests/test_unity_session_cli.py`: `ensure_session_ready` and `_invoke_exec` are not called, the exit code is 26, and repeated waits return the same status. Also verify that the existing `test_wait_for_exec_replays_pending_exec_*` tests still pass when no journal entry exists.
- [x] 2.4 In `exec`, after a `not_available` submit with a journal entry present, poll pid liveness for a 15s grace window (module constant, patchable in tests). Verify with tests for both branches: the process exits and returns exit 26, or it stays alive and returns `not_available` with the pending artifact kept.
- [x] 2.5 Add `editor_crashed_during_request` (exit 26) to the `exec` and `wait-for-exec` help failure tables and to the guidance matrix. `next_steps` offers a new `exec` and `get-log-source`, with no same-`request_id` continuation. Verify with help-surface tests and with `unity-puer-exec exec --help` output.

## 3. Documentation

- [x] 3.1 Document the new status in `README.md` and `README.zh-CN.md`, and add the PuerTS scripting note (passing `null` for a C# `out` parameter crashes the Editor natively; use `puer.$ref()`). Mirror it in the package README if that README carries scripting notes. Verify that `tests/test_package_layout.py` and the spec-hygiene tests still pass.

## 4. Integration validation

- [x] 4.1 Run the full unit suite (`python -m pytest tests -q`, excluding real-host tests) and confirm it is green.
- [x] 4.2 Add a real-host regression in `tests/test_real_host_integration.py`. It runs project-scoped `exec` with a script calling `CS.UnityEngine.Diagnostics.Utils.ForceCrash(...)`, then `wait-for-exec`. Assert exit 26, that no Unity process was relaunched by `wait-for-exec`, that `Temp/UnityPuerExec/Editor.log` still ends with the `Exec starting request=<rid>` line, and that a following `exec` with a new request id relaunches and completes normally with the old request never re-run. Run it against the validation host per `openspec/specs/validation-host-integration/how-to-run.md` and record the result.
- [x] 4.3 Run `openspec validate fix-exec-crash-replay-loop --strict` and fix any findings.

## Workflow follow-up

- Comment on and close GitHub issue #2 after release, linking the change.
- Archive with `openspec archive fix-exec-crash-replay-loop` after review, then make the final commit.
