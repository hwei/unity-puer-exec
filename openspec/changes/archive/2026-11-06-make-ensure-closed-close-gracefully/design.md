# Design

## Context

Current behaviour in `unity_session_process.ensure_closed` (project mode):

- **Decision rule.** "Stopped" means the project's Unity lockfile is not held
  (`formal-cli-contract`: project-local stop state). The kill target is only
  the pid that the project's own endpoint publication names.
- **`timeout_then_kill`, the default.** It polls the lockfile until
  `--timeout-seconds` and then runs `taskkill /PID <pid> /T /F`. Nothing ever
  asks Unity to quit, so the "graceful wait" only succeeds when something else
  happens to close the Editor.
- **The help.** It calls this "not the recommended graceful-exit path" and
  recommends `exec --file exit.js`.

Evidence from the 2026-11-06 probes (`archive/2026-11-06-stop-play-persisting-run-in-background/validation-transcript.md`):

- `EditorApplication.Exit(0)` called synchronously inside an exec script crashed
  the Editor twice, each time right after `[LAYOUT] About to save layout`.
- `(Get-Process -Id <unity_pid>).CloseMainWindow()` closed the Editor cleanly
  four times. It went through Unity's normal quit, including the
  project-settings save (case A3 persisted the in-memory value exactly as a user
  close would).

## Goals / Non-Goals

**Goals:**
- `ensure-closed` becomes the one obvious and safe way for an agent to close the
  Editor.
- Unsaved work is never discarded without being reported.

**Non-Goals:**
- Closing Editors that the project's publication does not name. The existing
  ownership rules stay.
- Base-url mode. It stays inspect-only.
- Detecting `EditorApplication.Exit` reached indirectly, for example through
  reflection or a helper assembly. The exec guard is a lexical check aimed at
  the common agent mistake.

## Decisions

### D1: Quit mechanism — `CloseMainWindow` (decided by task 1.1 probe)

Decided: **A. CLI-side `CloseMainWindow`.** The task 1.1 probe
(`validation-transcript.md`) found it is the only candidate that satisfies all
three criteria — clean exit with no crash report, a dirty in-memory project
setting saved, and an unsaved-scene save prompt shown. It needs no package
change, so it also works against older package versions on disk. It is
Windows-only, which the process-control code already is.

The rejected alternatives, and why:

- **B. A server-side quit action** that replies first, then calls
  `EditorApplication.Exit(0)` from `EditorApplication.delayCall`, so no script
  frame is on the stack. On this host the `delayCall` callback never ran at all,
  whether registered from the HTTP listener thread or via `MainThreadActions`.
  Calling `Exit(0)` directly on the main thread instead did exit cleanly and did
  save project settings, but it showed no save prompt and silently discarded a
  dirty scene — the exact loss of unsaved work D2 exists to prevent. B also
  needs a package change.
  Kept as a possible future fallback only for an Editor with no main window; the
  design does not depend on it, because `closed_via` and the modal-blocker
  handling are the same for both.

### D2: Modal blockers stop the wait

While waiting for the lockfile, the CLI polls the existing blocker detection
(`get-blocker-state` logic) at a coarse interval. When a supported blocker
appears, the command returns the existing `modal_blocked` status
(`EXIT_MODAL_BLOCKED`, 19) with that blocker's payload. It does not kill.

A dialog that is not in the catalog is not detected. In that case the timeout
escalates to a kill, as today, but now with `closed_via: killed` in the result,
so the kill is at least visible.

Alternative considered: always kill at the timeout, as today. Rejected because
that silently discards unsaved scene edits, which is the worst outcome for an
agent working in someone's project.

### D3: `closed_via` is additive

The success payload keeps `result.status: stopped` and adds
`result.closed_via`. Existing callers keep working. The real-host suite's
`_ensure_clean_test_boundary` keeps its `--immediate-kill` escalation on the
second attempt.

### D4: The exec guard is a lexical pre-submit check

`exec` scans the script text (inline `--code`, or `--file` contents) for
`EditorApplication.Exit` and for `EditorApplication` and `Exit` within one
member-access chain, ignoring whitespace. On a match it refuses before any
session or launch work.

- Status: `editor_exit_in_script`, with a new formal exit code. Assign the next
  free code, 27, and register it in the help status tables.
- The guidance names `ensure-closed`.

A refusal is better than a warning, because the crash is deterministic and
loses the agent's in-flight request and log context.

### D5: The real-host helper switches to `ensure-closed`

The `CloseMainWindow` helper in `PlayModeRunInBackgroundPersistenceRealHostTests`
becomes a call to `ensure-closed --project-path`, which asserts
`closed_via: graceful`. That makes the regression tests exercise the product
path itself.

## Risks / Trade-offs

- [`CloseMainWindow` finds no main window, for example during startup or with a
  minimized splash] → Treat a `False` return as "could not request quit": keep
  waiting and escalate at the timeout, with `closed_via: killed` and a
  diagnostic naming why the request failed.
- [Other Editor-side prompts, such as an "unsaved prefab" dialog or the
  ScriptUpdater consent, block the quit] → They are handled by D2 when
  cataloged. Otherwise they fall back to the disclosed kill.
- [Lexical guard false positive, for example a comment mentioning
  `EditorApplication.Exit`] → Accepted. The refusal message says so explicitly,
  and the caller can reword the comment.
