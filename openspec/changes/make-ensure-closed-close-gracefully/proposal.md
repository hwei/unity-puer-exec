# Proposal

## Why

Agents keep crashing the Unity Editor by calling `EditorApplication.Exit(0)` from
inside an `exec` script. The same thing happened twice during the
`stop-play-persisting-run-in-background` probe on 2026-11-06 (crash reports
`Crash_2026-11-06_032837754`, `_033043638`). The maintainer has seen it several
times before.

- **Why it crashes.** The Editor tears down V8 while the exec script is still
  on the stack.
- **Why agents do it.** The CLI points them there:
  - `ensure-closed --help` says it is "not the recommended graceful-exit path"
    and recommends "a script request such as `exec --file X:/exit.js`".
  - `ensure-closed` itself never asks Unity to quit. Its default mode only waits
    for the lockfile to be released and then runs `taskkill /F`. That skips
    Unity's settings save and discards unsaved work without saying so.

Related follow-up: `surface-editor-crash-on-any-transport-loss` reports these
crashes properly. This change removes the most common self-inflicted cause.

## What Changes

- **Graceful close becomes the default.** In project mode, `ensure-closed` first
  asks the Editor to quit through its normal quit path, the same way a user
  closing the window does. Only if the Editor is still running when the timeout
  ends does it escalate to a kill. The result reports how the Editor was closed:
  `closed_via` is `already_stopped`, `graceful` or `killed`.
- **A blocking dialog is reported, not killed.** If a supported modal blocker,
  such as a save-changes prompt, holds the quit, `ensure-closed` reports it with
  the existing modal-blocker status and `resolve-blocker` guidance. It does not
  kill the Editor and silently discard the unsaved work. `--immediate-kill` keeps
  its current meaning.
- **Help makes `ensure-closed` the recommended way to close the Editor.**
  - The `exec exit.js` recommendation is removed.
  - The help states that calling `EditorApplication.Exit` from an exec script
    crashes the Editor.
  - The top-level command list describes `ensure-closed` accordingly.
- **`exec` refuses an exit-the-Editor script.** Before submitting, it refuses a
  script whose source calls `EditorApplication.Exit`, and points the caller to
  `ensure-closed`.
- **Real-host suite.** The suite's own graceful-close helper, the
  `CloseMainWindow` call added for `PlayModeRunInBackgroundPersistenceRealHostTests`,
  switches to `ensure-closed`.

## Capabilities

### New Capabilities

- `editor-graceful-close`: how the CLI closes a project's Editor. It covers
  graceful quit first, then disclosed escalation, modal-blocker handling, and
  the guard against exiting the Editor from inside a script.

### Modified Capabilities

(none — the existing `formal-cli-contract` requirements on `ensure-closed`
already hold: it uses project-local stop state, never kills in base-url mode, and
kills only the project's own published process. The new behaviour is stated in
the new capability.)

## Impact

- **Package.** Possibly a new control-endpoint action that schedules a quit
  after replying, depending on the mechanism chosen by the probe in task 1.1.
- **CLI.**
  - `cli/python/unity_session_process.py` (`ensure_closed`) and
    `run_ensure_closed`;
  - the `exec` pre-submit path;
  - `help_surface.py`: `ensure-closed` quick start and status tables, the
    top-level command list, and the `exec` help.
- **Tests.** Mocked CLI and session tests; the real-host close helper in
  `tests/test_real_host_integration.py`; one real-host case each for a graceful
  close and a modal-blocked close.
- **Behaviour change.** The default mode no longer silently kills an Editor that
  is waiting on a save prompt.
