## Context

`refresh-on-change` made the play-mode case visible at the diagnostics level: the
tracker returns `play_mode`, the exec `refresh` block carries
`skipped_reason: "play_mode"`, and `/health` carries
`refresh.suppressed` / `refresh.suppressed_reason`. Those findings still hold. What
the earlier change did not do is make that visibility *actionable*:

```
agent edits .cs ──► exec (Editor playing)
                     server: Decide() -> play_mode, no refresh, script runs
                     CLI:    status "completed"   ◄── reads like success
agent: wait-for-compile
                     appear window elapses -> "no_compile_observed"
                     guidance: "trigger RequestScriptCompilation()"   ◄── wrong remedy
```

The agent does not know the code is stale, the guidance sends it in the wrong direction,
and the CLI has no way to stop play mode yet. That last gap is `add-play-mode-commands`;
this change owns diagnosis and guidance.

Facts from the tree5 host (non-normative):
- `Entering Playmode with Reload Domain disabled` / `Reload Scene disabled`: Enter Play
  Mode Options are on.
- The project registers `EditorApplication.playModeStateChanged`
  (`GlobalHttpClient.cs:110`), and that handler runs on exit.
- Both play exits in the surviving log came from the toolbar Play button, so the
  failing agent attempt is not in it.

## Goals / Non-Goals

**Goals:**
- An agent that runs code in play mode with a pending change is told so in the status it
  branches on, not only in a diagnostics block.
- `wait-for-compile` names the play-mode block instead of reporting
  `no_compile_observed`.
- Guidance leads out of play mode and never suggests forcing a compile during play.
- Root-cause the "cannot stop play mode" report.

**Non-Goals:**
- `play` / `stop` / `pause` commands and `runInBackground` (see `add-play-mode-commands`).
- Refreshing or compiling during play mode, even when the "Script Changes While Playing"
  preference would let Unity do it. The suppression stays. The preference is only
  reported, because a reload during play loses play state and, with Reload Domain
  disabled, behaves differently from what agents expect.
- Changing the CLI-side settle/resubmit loop.

## Decisions

### D1. Exec reports `status: "warning"` rather than a new non-success status

The script did run, so `ok: true` stays correct, and `exec-warning-status` already
defines "ran, but there is a caveat you must read" with exit code 0. A failure-class
status would break callers that legitimately run play-mode scripts against unchanged
code. Those callers see no change, because the warning is raised only when a change is
actually pending.

*Collision with `async_result_not_supported`*: the response has one `warning` code. The
async warning keeps the code, because it concerns the result the caller is reading, and
the `compile_blocked` object is attached in both cases. So the object, not the code, is
the reliable signal. Considered and rejected: a `warnings[]` list, which would change an
established response shape for one edge case.

### D2. `compile_blocked` is a top-level response object

```
"compile_blocked": {
  "reason": "play_mode",
  "pending_paths": ["Assets/.../Foo.cs"],          // when known, bounded like refresh.paths_changed
  "script_changes_while_playing": "recompile_after_finished_playing"
}
```

It is derived from data the server already returns: `refresh.skipped_reason` and
`refresh.paths_changed` on exec, and `refresh.suppressed` plus the new preference field
on health. The CLI composes it, so no new exec protocol field is needed.

### D3. `wait-for-compile` checks health before its appear window

The CLI already polls `/health`. Before entering the appear phase, if `compiling` is
false, `refresh.pending` is pending, and `refresh.suppressed` is true with reason
`play_mode`, it returns `compile_blocked` immediately. An already-running compile in
play mode still settles normally (D3 does not pre-empt an observed compile edge).

### D4. Preference read is server-side

`EditorPrefs.GetInt("ScriptCompilationDuringPlay")` (0 / 1 / 2 →
recompile_and_continue_playing / recompile_after_finished_playing /
stop_playing_and_recompile) is sampled on the main thread in `OnEditorUpdate`, the same
tick that already caches `isPlaying` / `isCompiling`, and stored in a volatile field. The
health handler runs off the main thread and cannot call `EditorPrefs`. The key name is an Editor implementation detail, so a missing key or an
unexpected value reports `unknown` rather than guessing.

### D5. Interim continuation uses `exec`

Until `stop` exists, `next_steps` uses an `exec` that sets
`EditorApplication.isPlaying = false`, then a play-state confirmation, then
`wait-for-compile`. This is the sequence the current PlayMode help already describes.
`add-play-mode-commands` replaces the first two steps with `stop`.

### D6. "Cannot stop play mode" is investigated before it is fixed

Hypotheses, in the order they are cheapest to rule out on the validation host:

1. **The stop was requested, not completed.** The exec that sets `isPlaying = false`
   returns success at once, and the agent read a later `isPlaying == true` as failure.
2. **Exiting play starts the deferred compile and domain reload.** The server goes down
   during the reload, and the agent's next probe fails or times out, which looks like
   "stop failed". This is likely with `recompile_after_finished_playing`.
3. **A modal dialog on exit** (for example, save scene or a project dialog) blocks the
   transition.
4. **The project's `playModeStateChanged` handler** throws or blocks during
   `ExitingPlayMode`.
5. **Editor paused** combined with Enter Play Mode Options.

The fix depends on which of these holds. 1 and 2 are CLI or guidance fixes within this
change. 3 is routed to the existing blocker surface. 4 is host-specific and only
recorded. 5 is passed on to `add-play-mode-commands`.

## Risks / Trade-offs

- [Callers that branch only on `status == "completed"`] → they now see `warning` in play
  mode with a pending change. That is intended: their previous "success" ran stale code.
  The exit code stays 0.
- [`pending_paths` false positives from the scan] → shown as "when known"; the warning
  is driven by the same pending decision the refresh already trusts.
- [Preference key changes across Unity versions] → `unknown` fallback, covered by a unit
  test against an absent key.
- [Coupling to `scan-only-import-change-signal`] → that change removes the watcher-backed
  `unknown` pending state, and this change reads only `pending` / `not_pending`. Either
  order works; landing scan-only first avoids handling `unknown` here.

## Open Questions

- If the tree5 agent transcript can be recovered, it would confirm or rule out D6
  hypotheses 1–2 before any reproduction work.
