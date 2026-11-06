# Design

## Context

What still holds from `add-play-mode-commands` (design D5):

- `Application.runInBackground` resets from Player Settings when play mode
  starts.
- Entering play mode may reload the script domain.
- The request is therefore passed through `SessionState`, and the
  `[InitializeOnLoad]` hook in `UnityPuerExecPlayMode` applies it on
  `EnteredPlayMode`.

The gap is that the current code writes the value at two sites:

1. `UnityPuerExecServer.HandlePlayModeAsync` assigns
   `Application.runInBackground = true` in **edit mode**, just before it sets
   `EditorApplication.isPlaying = true`. D5 did not call for this assignment.
   It was added in commit `3af69aa` without a stated reason.
2. `UnityPuerExecPlayMode.OnPlayModeStateChanged` assigns the value on
   `EnteredPlayMode`, when the Editor is already in play mode.

Behaviour the maintainer has observed: changing `runInBackground` while in play
mode is not persisted to the project. So site 2 should be harmless, and site 1,
an edit-mode write, is the likely source of the `runInBackground: 1` found in
`ProjectSettings.asset` after the Editor exited.

Why the original validation missed it: the `add-play-mode-commands` transcript
records that the host's `PlayerSettings.runInBackground` was already `true`. A
forced write of `true` leaves no diff. Every probe in this change therefore
starts from a host value of `0`.

## Goals / Non-Goals

**Goals:**
- After any forced play session, the host's `ProjectSettings.asset` on disk is
  byte-identical to before. This holds whether the session was stopped first or
  the Editor exited during play.
- Keep the observable `play` contract: forced by default, disclosed in the
  result, opt-out with `--no-run-in-background`. Keep the measured effect: an
  unfocused Editor keeps advancing frames.

**Non-Goals:**
- Changing the Interaction Mode throttle. The `add-play-mode-commands`
  disposition already settled it.
- Hard Editor crashes. A crashing Editor saves no settings.

## Decisions

### D1: Write only during play mode

Remove the edit-mode assignment in `HandlePlayModeAsync`. The play-mode hook
becomes the only writer. That uses the play-mode behaviour above and needs no
new state.

The `SessionState` request/cancel path stays unchanged. Comments that say "never
written back to Player Settings" are rewritten to describe what actually holds:
the override is applied only after play mode is entered, so Unity does not
persist it.

Alternative considered: snapshot `PlayerSettings.runInBackground` and restore it
on `EnteredEditMode` / `EditorApplication.quitting`. Rejected as the primary
approach because it adds state and restore paths to solve a problem that one
deleted line may already solve. It is kept as D2.

### D2: Fallback, used only if the probe fails

If probe case C (the Editor exits during play) still persists the value, add a
snapshot/restore:

- Record the project value in `SessionState` once per session.
- Restore it through `PlayerSettings.runInBackground` on `EnteredEditMode` and
  in an `EditorApplication.quitting` handler.

The fallback triggers only on that finding. Task 1.1 records which branch was
taken.

### D3: The probe decides the design before any code changes

Use a `.tmp/` probe on the real host with the host value set to `0`. Before each
case, reset `ProjectSettings.asset` from git.

| case | package state | sequence | expected |
|---|---|---|---|
| A | current | forced `play` → `stop` → close Editor | asset gains `runInBackground: 1` (reproduces the bug) |
| B | edit-mode assignment removed | forced `play` → `stop` → close Editor | asset unchanged |
| C | edit-mode assignment removed | forced `play` → close Editor without `stop` | asset unchanged |
| D | edit-mode assignment removed | forced `play`, Editor unfocused, `Time.frameCount` delta over 6 s | far above the ~83 frames from the throttled baseline in the `add-play-mode-commands` transcript |

Outcomes:

- A does not reproduce: the hypothesis is wrong. Set `assumption_state` to
  `invalid` and revisit the design.
- B or D fails: D1 is not enough. Revisit the design.
- Only C fails: take D2.

### D4: Real-host regression compares the file bytes

Turn cases B and C into pristine-process real-host tests next to
`PlayModeCompileBlockRealHostTests`. Each one sets the host value to `0`,
records the `ProjectSettings.asset` bytes, runs the sequence, closes the Editor,
and compares the bytes. Comparing bytes also catches incidental settings writes.
Setting the value to `0` first is required, because a host that already holds
`1` would hide the bug, which is how the original validation missed it.

## Risks / Trade-offs

- [The edit-mode assignment existed for a reason that was never written down,
  such as keeping the frame rate up on the first frames of a domain-reloading
  entry] → Case D measures that directly. If D regresses, revisit the design
  instead of putting the line back.
- [Unity's "play-mode changes are not persisted" behaviour differs across Unity
  versions] → The real-host regression pins it for the validation host's
  version. If a different Unity version shows a write, D2 is the ready answer.
