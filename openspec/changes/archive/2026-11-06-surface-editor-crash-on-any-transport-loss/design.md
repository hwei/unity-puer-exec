# Design

## Context

What still holds from the existing `editor-crash-surface` work:

- The service journals each exec request before running it. The journal entry
  records the Editor pid and `process_start_utc`.
- Project-scoped `exec` / `wait-for-exec` refuse to relaunch or replay a request
  whose journalled Editor is gone.
- After a `not_available` drop, `exec` watches the journalled pid for
  `EDITOR_CRASH_GRACE_SECONDS` (15 s). Unity's crash handler keeps the process
  alive while it writes the dump, which is why a grace window is needed.
- `_emit_editor_crash_payload` and `_find_editor_crash_report_dir` already build
  the crash payload and locate its evidence.

The gaps, observed on the real host on 2026-11-06 (see proposal.md):

1. `run_exec` only enters the grace check through `_is_not_available_response`.
   A crash that surfaces as `empty_response` (exit 12) skips the check.
2. `_post_play_mode` classifies both `empty_response` and `not_available` as
   `_is_play_mode_transport_drop` and retries until `timeout_seconds` is used up.
   Nothing checks the Editor process. `wait-for-compile` and the compile-error
   and compile-warning queries also have no crash check.

## Goals / Non-Goals

**Goals:**
- Any transport loss against a project whose Editor process has died is
  reported as a crash, promptly, with evidence, and without relaunching Unity.
- Genuine domain reloads, where the process stays alive, keep their current
  retry behaviour and gain no new latency.

**Non-Goals:**
- Crash detection for `--base-url` targets. There is no process handle, so they
  keep their transport statuses.
- Preventing the self-inflicted `EditorApplication.Exit` crash. That belongs to
  the separate `ensure-closed` follow-up.
- Commands that do not talk to the control endpoint (`ensure-closed`,
  `get-log-source`, `get-log-briefs`).

## Decisions

### D1: One shared "published Editor exited" check

Add a helper that takes the pid of the Editor the command is talking to and
answers three ways: `alive`, `exited`, or `unknown` (no pid).

- The pid comes from the session that `ensure_session_ready` returned, or else
  from the endpoint publication read at command start. The publication is not
  removed when the Editor crashes, so the pid stays readable after the drop.
- The existing `_wait_for_journaled_editor_exit` becomes a thin wrapper over the
  same pid watch.

Alternative considered: decide on the basis of a fresh crash report directory
alone. Rejected. Unity writes the report while the process is still alive, and
a report can belong to another project's Editor on the same machine (tree3 runs
in parallel on this host). The report is evidence only; the pid decides.

### D2: Retry loops check the pid on every iteration; grace waiting happens only at the edge

- **Play-mode loop and compile-query paths.** On each transport-drop iteration,
  do a non-blocking `is_pid_running(pid)` check before re-resolving. A dead pid
  ends the loop with the crash payload.

  This adds no latency to reloads: a reloading Editor's pid stays alive, so the
  check passes and the loop proceeds as today.

  A crash is caught within one poll interval of the crash handler finishing,
  which takes a few seconds, instead of after the whole budget.

  When the budget elapses with the pid still alive, a single bounded grace
  watch runs before the transport status is reported. That catches a crash
  handler that is still writing the dump at the deadline.
- **Exec.** Widen the existing branch from `not_available` to
  `not_available or empty_response`, using the shared predicate behind
  `_is_play_mode_transport_drop` minus its 404 and `failure_origin` exclusions.
  Exec keeps its 15 s grace wait, because there the journal already proves the
  script started.

### D3: Reuse `editor_crashed_during_request` and exit 26

Callers already branch on this status and exit code for `exec`, and the help
already explains it.

- A non-exec payload has no `request_id` and no `resubmit_safe`, because there
  is no script to replay.
- It carries `operation`, `editor_pid`, `started_at` (the command start, used
  for the crash-report lookup), `editor_log_path`, `crash_report_dir`, the
  `situation` and the `next_steps` that the spec delta defines.

Alternative considered: a new `editor_crashed` status. Rejected because it adds
a second name for the same caller decision ("the Editor is gone, inspect and
rerun"), and because existing exec callers would gain nothing from it.

### D4: Guidance for transport statuses depends on whether the Editor is alive

The `empty_response` and `not_available` guidance keeps its domain-reload
wording. That is now accurate, because a dead Editor is no longer reported
through these statuses in project mode. Base-url mode, which cannot see the
process, gets one added clause: if the Editor process is gone, treat it as a
crash. No other help text changes.

### D5: Real-host evidence uses a deliberate crash, never `EditorApplication.Exit`

- **Play case.** A temp-asset script under the repository-owned validation temp
  folder, with `[RuntimeInitializeOnLoadMethod]`, calls
  `UnityEngine.Diagnostics.Utils.ForceCrash(ForcedCrashCategory.AccessViolation)`.
  Run `play` and assert exit 26 well inside `--timeout-seconds`, plus
  `crash_report_dir`.
- **Exec case.** An exec script calls `Utils.ForceCrash` directly. Assert that
  exit 26 is returned whichever transport shape the drop takes.
- Both are pristine-process cases. The cleanup tool removes the temp script
  afterwards, so the next launch cannot crash on play again.

## Risks / Trade-offs

- [pid reuse: a new process takes the dead Editor's pid within seconds] → Very
  unlikely inside one command. The exec path still compares the journal's
  `process_start_utc` where it has it.
- [A reload where the Editor really restarts, so the pid changes] → Unity does
  not restart the process on a domain reload. A changed publication pid with the
  old pid dead is a different Editor. Reporting it as an exited Editor is
  correct.
- [ForceCrash leaves crash reports and dumps behind] → Expected. They are under
  `%TEMP%`, outside the host project, and are the evidence under test.
