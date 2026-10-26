# Design

## Context

See proposal.md (Why) for the crash loop. Facts this design depends on:

- Server job records (`Requests`, `UnityPuerExecJob`) live only in memory and die with the Editor process. No server-side record survives a crash.
- The CLI-side pending artifact (`Temp/UnityPuerExec/pending_exec/<rid>.json`) holds the full script. It exists so that requests the server never accepted (startup not ready, refreshing, compiling) can be replayed later. `_should_keep_pending_after_submit` also keeps it after `not_available`, which is the ambiguous case where the server may already have started the script.
- `StartJobEvaluation` runs on the main thread and calls `jsEnv.ExecuteModule` synchronously. Every terminal path goes through `ReleaseActiveRequest`.
- A CLI-launched Editor writes to `Temp/UnityPuerExec/Editor.log`. A relaunch with `-logFile` truncates that file, so an automatic relaunch destroys the crash tail.
- On Windows, Unity writes crash reports to `%TEMP%\Unity\Editor\Crashes\Crash_<date>_<time>\` (the issue shows `Crash_2026-10-26_0629…`).

## Goals / Non-Goals

**Goals:**
- A request whose script started is executed at most once, even across Editor crashes.
- The caller gets a distinct, terminal crash outcome with evidence, from the first command that can know.
- The crash evidence (Editor log, crash report) is preserved, not overwritten by a relaunch.

**Non-Goals:**
- Jobs lost to a domain reload in the same Editor process (async scripts that span a reload). The journal records enough to detect this later (same pid, no in-memory job), but this change keeps that path as it is. It is listed as a follow-up candidate.
- Fixing PuerTS's native crash on `null` for `out` parameters. That is upstream; this change only documents the workaround.
- A general relaunch cap. With the guard in place, a deterministic crash produces exactly one crash per request, so a separate cap adds nothing.

## Decisions

### D1. The journal is written by the server, not the CLI

The CLI cannot tell "sent, not started" apart from "started, then crashed": both look like a dead connection. Only the server knows that `ExecuteModule` is about to run. The entry is written synchronously on the main thread immediately before `ExecuteModule` and after all early-failure checks (JsEnv missing, wrapper build failure), so its existence means "script execution began".

Alternative considered: the CLI marks the pending artifact as "submitted" before sending and refuses to replay it after `not_available`. Rejected: that would also block legitimate replays where the server never accepted the request (for example, the connection dropped during compile), and it would not protect `--base-url` callers.

### D2. Journal layout and identity

- Path: `<project>/Temp/UnityPuerExec/exec_journal/<key>.json`, a sibling of `pending_exec/`. `<key>` is the `request_id` when it matches `^[A-Za-z0-9._-]{1,128}$`; otherwise it is the lowercase hex SHA-256 of the UTF-8 `request_id`. The CLI and the server use the same rule.
- Content: `{ "schema_version": 1, "request_id", "editor_pid", "process_start_utc", "started_at_utc", "editor_log_path" }`. Times are ISO-8601 UTC. `editor_log_path` is the server's `Application.consoleLogPath`, which is useful for an Editor the CLI did not launch.
- Written with write-to-temp-then-rename so that a reader never sees a half-written file.
- "Different process" means `editor_pid` differs, or `process_start_utc` differs (to guard against pid reuse).

### D3. Removal at terminal outcome happens in `ReleaseActiveRequest`

Every terminal path (`CompleteJob`, `FailJob`, `CompleteJobWithWarning`, exceptions in `StartJobEvaluation` and in the enqueue lambda) already calls `ReleaseActiveRequest`, so that is the one place that deletes the entry. Delete failures are logged and ignored: a leftover entry for the *current* pid is never treated as a crash.

### D4. Server guard

In `TryAcceptExecRequest`, before creating a new job: if there is no in-memory record for `rid` and a journal entry exists from a different process, return a new accept status `editor_crashed`. The handler answers with `BuildEditorCrashedResponseJson` (status `editor_crashed_during_request`, `editor_pid`, `started_at`, `editor_log_path` from the entry) and does not enqueue anything. The guard runs before the content-equivalence and `busy` checks, because a crashed request is terminal no matter what is active now. `HandleWaitForExecAsync` applies the same check before answering `missing`.

### D5. CLI check order (project mode)

In both `exec` and `wait-for-exec`, the journal is read **before** `ensure_session_ready`:

1. Sweep expired or malformed journal entries (24h, same as pending).
2. If an entry for `rid` exists and `editor_pid` is not running (`is_pid_running`), build the crash payload, clear the pending artifact, and return exit 26. Unity is not launched.
3. Otherwise continue as today.

`exec` adds one more check after the submit returns `not_available`. If an entry for `rid` now exists, the CLI polls `is_pid_running(editor_pid)` for a short grace window (default 15s; Unity's crash handler keeps the process alive while it writes the dump). If the process exits within the window, the crash payload is returned. If not, `exec` returns its current `not_available` and keeps the pending artifact. The next `wait-for-exec` reaches step 2 once the process is gone. If something relaunches the Editor first, the server guard (D4) still refuses to run the script.

Alternative considered: relaunch the Editor and then report the crash, so the Editor is back up. Rejected: the relaunch truncates `Temp/UnityPuerExec/Editor.log` and hides the evidence, which is exactly the masking the issue complains about. The next project-scoped command relaunches anyway.

### D6. Evidence enrichment on the CLI side

The CLI fills in `editor_log_path` (journal entry, falling back to the resolved project log path) and `crash_report_dir`. For `crash_report_dir` it takes the newest `Crash_*` directory under `tempfile.gettempdir()/Unity/Editor/Crashes` whose mtime is at or after `started_at - 5s`, or omits the field when there is none. It also adds `log_range` as every other exec response does. The same enrichment is applied when the status comes from the server guard (D4), so both paths produce the same payload.

### D7. Status and exit code

The status is `editor_crashed_during_request` (the name suggested in the issue, and it says exactly what happened). Exit code 26 is the next free code after `refresh_unsettled` (25). `resubmit_safe: false` and `recoverable: false`. `next_steps` offers `exec` for a new request id after the script is fixed, and `get-log-source` / reading the Editor log. It deliberately offers no same-`rid` continuation.

## Risks / Trade-offs

- [The Editor exits for an unrelated reason (the user closes it, or the OS kills it) while a script runs] → It is still reported as `editor_crashed_during_request`. That is correct from the caller's point of view: the process died mid-request, so the request must not be re-run. The `situation` says "most likely" rather than claiming the script was the cause.
- [The crash handler keeps the process alive longer than the grace window] → `exec` returns `not_available` as it does today. The following `wait-for-exec` reports the crash once the process exits. If the Editor is relaunched in between, the server guard catches it.
- [Synchronous file write on the main thread before every exec] → One small JSON file per exec. The cost is negligible next to script execution.
- [A new CLI against an old package] → No journal is written, so the CLI behaves as it does today. [An old CLI against a new package] → The server guard still prevents re-execution. The old CLI surfaces the unknown status through its generic failure path.
- [Pid reuse] → Mitigated by comparing `process_start_utc` on the server. The CLI only checks whether the pid is alive, so in the rare reuse case it falls through to the server guard.

## Migration Plan

No data migration. The package and the CLI ship together in the next release. Rolling back removes the guard and the journal. Leftover journal files are harmless, because `Temp/` is disposable.
