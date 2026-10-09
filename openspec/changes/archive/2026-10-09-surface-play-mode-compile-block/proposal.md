## Why

On the `c3-client-tree5` host, an agent was stuck with the Editor in play mode: its C#
changes would not compile, and it could not get the Editor out of play mode. The CLI
gave it no explanation and no way forward.

Reading the code shows why the CLI is silent:

- `refresh-on-change` skips the automatic refresh while the Editor is playing
  (`UnityPuerExecImportChangeTracker.Decide` → `reason: "play_mode"`). The script still
  runs, the response is `status: "completed"`, and the only trace is
  `refresh.skipped_reason: "play_mode"` in the diagnostics block. That is
  spec-conformant ("Exec during play mode skips refresh visibly"), but nothing tells the
  agent that it just ran **stale code**, or what to do about it.
- `/health` already reports `refresh.suppressed: true` / `suppressed_reason: "play_mode"`,
  but no Python CLI code reads that field.
- `wait-for-compile` in play mode waits out the appear window and returns
  `no_compile_observed`. Its guidance then suggests calling
  `CompilationPipeline.RequestScriptCompilation()`, which cannot help: Unity defers that
  compile until play mode exits too. The guidance points the agent the wrong way.

The second half of the report, that the Editor could not be stopped, is unexplained.
tree5's project-private `Editor.log` shows `Entering Playmode with Reload Domain disabled`
(Enter Play Mode Options are on) and a project `OnPlayModeStateChanged` handler
(`GlobalHttpClient.cs:110`) that runs on exit. Both play exits recorded in the log came
from the toolbar Play button; the failing agent transcript is not available. The failure
has to be reproduced before it is fixed.

## What Changes

- **Investigate "cannot stop play mode"** on the validation host. Candidate causes are
  listed in design.md; reproduce first, then fix within this change if the fix belongs to
  the CLI or the package, or record it as host-specific.
- **Name the blocked state.** When a compile-triggering change is pending and the Editor
  is in play mode, `exec` and `wait-for-compile` report a machine-readable
  `compile_blocked` condition. It carries the reason (`play_mode`), the pending paths when
  known, and the Editor's "Script Changes While Playing" preference, so the agent can see
  why the compile is not happening.
- **Give the next step.** These responses carry `situation` and `next_steps` that say
  the code will not compile until play mode exits and show how to exit it. Until
  `add-play-mode-commands` lands, the continuation is an `exec` that sets
  `EditorApplication.isPlaying = false`, followed by the confirm-then-continue sequence.
- **Fix the misleading guidance.** `wait-for-compile` no longer returns
  `no_compile_observed` with `RequestScriptCompilation()` advice when the real cause is
  play mode.
- `exec` still runs the script in play mode, which keeps the existing scenario intact.
  The response becomes `status: "warning"` with `warning: "compile_blocked_by_play_mode"`
  instead of a plain `completed`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `import-change-refresh`: "Play mode skips the refresh without discarding the change
  signal" gains a required `compile_blocked` disclosure and a warning status on the exec
  response, so that a play-mode skip with a pending change is never reported as a plain
  success.
- `compile-wait`: adds a distinct `compile_blocked` outcome for a pending change that
  cannot compile because the Editor is in play mode, separate from `no_compile_observed`.
- `runtime-guidance`: the new outcome and warning carry `situation` and `next_steps` that
  lead out of play mode.
- `project-control-endpoint`: the health suppression block also reports the Editor's
  "Script Changes While Playing" preference.

## Impact

- `cli/python/unity_puer_exec_runtime.py`: the exec refresh block is read for
  `skipped_reason == "play_mode"` and the warning is built; `_run_wait_for_compile_impl`
  reads `refresh.pending` / `refresh.suppressed` from health before declaring
  `no_compile_observed`.
- `cli/python/help_surface.py`: guidance entries for the new outcome and warning, and
  `--help-status` text.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` and
  `UnityPuerExecProtocol.cs`: the health block reports the preference, plus whatever the
  stop-play investigation requires.
- Tests: `tests.test_unity_session_cli` (exec and wait-for-compile play-mode cases), the
  help-content cases, and a real-host play-mode case.
- Downstream: `add-play-mode-commands` (blocked by this change) replaces the exec-based
  continuation with `stop`.
