# Validation transcript — stop-play-persisting-run-in-background

## Task 1.1 probe (2026-11-06)

- Probe: `.tmp/rib_persist_probe.py`, host `c3-client-tree2/Project`, Unity 2022.3.62f2.
- Starting state: committed `runInBackground: 0`. The host was prepared with
  `prepare_validation_host.py` after `--clear-embedded-shadow`. The baseline
  bytes were restored after every case.
- How the Editor was closed:
  - First attempt: `EditorApplication.Exit(0)` called synchronously inside an
    exec script. This **crashed the Editor** twice, because V8 was torn down
    mid-call (crash reports `Crash_2026-11-06_032837754` and `_033043638`). This
    is not a product defect of this change; see follow-ups.
  - All later cases send `CloseMainWindow()` to the Editor's main window, the
    same path as a user clicking the window's close button.

| case | package | sequence | `PlayerSettings.runInBackground` after stop | asset after save/close |
|---|---|---|---|---|
| A2 | unchanged | forced play → SaveAssets in play → stop → SaveAssets → Exit(0) | `true` (polluted) | in play: unchanged; **after stop + SaveAssets: `1`** |
| A3 | unchanged | forced play → stop → close window (no explicit save) | `true` (polluted) | **after close: `1`** |
| B | edit-mode assignment removed | forced play → SaveAssets in play → stop → SaveAssets → close window | `false` | unchanged at every step |
| C | edit-mode assignment removed | forced play → SaveAssets in play → close window while playing | n/a | unchanged at every step |

Frame-rate check: in every forced case, `Application.runInBackground` was `true`
while playing, with 462–530 frames in 6 s. That includes B and C, where only the
`EnteredPlayMode` hook applies the override. The add-play-mode-commands
transcript recorded 83 frames for the throttled baseline. Removing the edit-mode
assignment does not affect the override.

## Findings

- Mechanism: the edit-mode assignment `Application.runInBackground = true` in
  `HandlePlayModeAsync` writes the in-memory `PlayerSettings.runInBackground`
  before play mode starts. Unity snapshots project settings on entering play
  mode, so this value survives `stop`. The next project-settings save, whether
  an explicit `AssetDatabase.SaveAssets` or a normal Editor close, then persists
  it.
- Writes made while in play mode are reverted when play mode exits and are not
  persisted. That includes `SaveAssets` during play and closing the Editor during
  play.
- Decision: design D1 alone is sufficient, so the D2 fallback is not needed.
  `assumption_state: valid`.

## Tasks 4.1 / 4.2 real-host run (2026-11-06)

- `PlayModeRunInBackgroundPersistenceRealHostTests` (2 cases: stop-then-close and close-while-playing) plus
  `PlayModeCompileBlockRealHostTests` (7 cases): `Ran 9 tests in 981.408s`, `OK`.
- Fail-against-pre-change: with the edit-mode assignment temporarily restored,
  `test_stop_then_close_leaves_project_settings_byte_identical` failed with
  `line 83: runInBackground: 0 -> 1`. The fix was then put back.
- No new Unity crash report during these runs.
- Host teardown: `cleanup_validation_host.py`, then `prepare_validation_host.py --restore-manifest` (`restored`,
  manifest.json and packages-lock.json, nothing left in place), then `--restore-embedded-shadow` (`restored`).
  After that, `git -C c3-client-tree2 status --short` was empty, and `ProjectSettings.asset` still read
  `runInBackground: 0`.
