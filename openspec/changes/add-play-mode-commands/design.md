## Context

This change follows `surface-play-mode-compile-block`. These findings from that change
still hold:

- The server skips automatic refresh during play (`play_mode`). That change now reports
  it as a warning and a `compile_blocked` outcome, with health carrying the "Script
  Changes While Playing" preference.
- Its interim way out of play mode is an `exec` that sets `isPlaying = false`, followed
  by confirm and wait. That is the multi-step sequence these commands replace.
- Its D6 investigation decides whether `stop` needs extra handling (pause interaction,
  project `playModeStateChanged` handlers). Read its recorded outcome before task 3.

The server already samples `isPlaying` in `OnEditorUpdate`, and the CLI already owns a
refresh → settle → resubmit loop on a compile-scale budget (`73811f4`). Both are reused
here.

## Goals / Non-Goals

**Goals:**
- One call per play-state change, returning only when the change has happened.
- No play session starts on stale code, and no edit session follows `stop` with an
  unsettled compile.
- The game loop keeps running while the Editor is unfocused, by default and
  reversibly.
- `stop` cannot be mistaken for closing the Editor.

**Non-Goals:**
- Input simulation, frame stepping, or Time.timeScale control.
- Changing Enter Play Mode Options. The commands work with either domain-reload setting.
- Removing `ensure-stopped`. It stays as an alias, and removal is a later decision.

## Decisions

### D1. Server endpoint plus health `play_state`, not an internal exec script

`POST /play-mode {action: "play"|"pause"|"stop", force_run_in_background: bool}`
enqueues the main-thread action and returns at once with the play state it observed.
Health gains `play_state`, derived each tick:

| condition | play_state |
|---|---|
| `!isPlaying && !isPlayingOrWillChangePlaymode` | `edit` |
| `!isPlaying && isPlayingOrWillChangePlaymode` | `entering` |
| `isPlaying && !isPlayingOrWillChangePlaymode` | `exiting` |
| `isPlaying && isPaused` | `paused` |
| `isPlaying` | `playing` |

The CLI polls health until it reaches the target state. Alternatives considered: an
internal `exec` script, which needs JsEnv to be ready, runs through the single-active-request
slot, and cannot observe a transition that reloads the domain. Polling `isPlaying` through
repeated execs, which is slow and blocked by an active request. The endpoint keeps
play control independent of script execution.

*Compatibility*: an older package has no `/play-mode`. The CLI reports the existing
version-mismatch result (exit 24) instead of a generic HTTP failure.

### D2. Waiting survives domain reloads

With Reload Domain enabled, entering and leaving play mode both reload the domain, and
the listener goes down for a moment. The CLI's wait loop treats a connection failure
during `entering` / `exiting` as expected and re-resolves the endpoint with the existing
range-aware discovery, up to the budget. That is the same recovery `exec` uses after an
automatic refresh.

### D3. `play` pre-settle reuses the exec refresh path

`play` first asks the server for a refresh decision through the same path `exec` uses.
If the decision triggers a refresh, the CLI runs `_settle_after_automatic_refresh`. On
`unity_compile_error`, it returns exactly what `exec` returns and never posts
`/play-mode`. The refresh decision moves behind a small server call so it no longer
needs an exec request. The extraction is part of task 3.1.

### D4. `stop` settles the deferred compile

`stop` reads `refresh.pending` from health before posting. After `edit` is reached, if
a change was pending, it runs the compile-wait loop with the compile-scale settle budget
and reports `compile: {outcome: "completed"|"compile_errors"|"no_compile_observed"}`.
Errors stay `status: "completed"`, because the play-state request succeeded, and carry a
`get-compile-errors` next step (spec: "Stop settles the compile cycle deferred by play
mode").

### D5. `runInBackground` via SessionState plus `EnteredPlayMode`

`Application.runInBackground` resets from Player Settings when play mode starts, and the
domain may reload during the start. The `/play-mode` handler therefore stores
`UnityPuerExec.ForceRunInBackground` in `SessionState`, which survives a domain reload.
An `[InitializeOnLoad]` `playModeStateChanged` hook applies it on `EnteredPlayMode`,
then clears the key. The project setting is read from `PlayerSettings.runInBackground`
for disclosure only. Player Settings are never written, which keeps `ProjectSettings.asset`
clean under git.

The Editor's own throttling while unfocused (Preferences → General → Interaction Mode)
can also slow the loop. That is a different setting. It is recorded as a real-host check
in task 5.2, not changed by this change.

### D6. Command group and the rename

`play` / `pause` / `stop` go into "Primary Execution" next to `exec`, because they are
high-frequency. `ensure-closed` replaces `ensure-stopped` in "Secondary /
Troubleshooting". The registry gains an alias table (`ensure-stopped → ensure-closed`).
Parser, help tiers, and guidance derive alias entries from it, so the "invocable set ==
documented set" invariant still holds. Alias responses add
`deprecated: {alias: "ensure-stopped", use: "ensure-closed"}`. Result statuses (`stopped`,
`not_stopped`) and exit codes do not change, so callers that branch on them are
unaffected.

### D7. Pause semantics

`pause` sets `EditorApplication.isPaused = true` and needs the Editor to be playing. In
edit mode it returns `invalid_play_state` (an expected machine state with a non-zero
exit code) and suggests `play`. `play` while paused clears `isPaused` and reports
`transition: "resumed"`.

## Risks / Trade-offs

- [Project `playModeStateChanged` handlers that block or throw] → the transition stalls,
  and `running` plus the blocker surface make that visible. tree5 has such a handler.
- [`play` gets slower when a change is pending] → intended. Without the pre-settle the
  session would run stale code. The result discloses the refresh.
- [The rename confuses existing host skills] → the alias keeps them working, and its
  deprecation field tells agents to migrate.
- [`runInBackground` forcing changes game behavior under test] → it is disclosed in every
  `play` result and can be turned off with `--no-run-in-background`.
- [Health polling granularity] → transitions are frame-bound, and polling at the existing
  readiness interval is enough.

## Migration Plan

1. Land the rename and alias first (task group 1) without behavior changes. All
   existing tests should pass with only name updates.
2. Add the server endpoint and health field. An older CLI ignores them.
3. Add the commands. Switch the `surface-play-mode-compile-block` guidance to `stop`.

Rollback: revert the commands. The alias and rename can stay on their own.
