# Validation evidence

## D6 "cannot stop play mode" reproduction (task 1.1)

Validation host: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`, Unity 2022.3.62f2,
Enter Play Mode Options on (`Entering Playmode with Reload Domain disabled`).

Procedure (`.tmp/repro_play_stop.py`): for each "Script Changes While Playing" setting, set the
preference, enter play mode, write a real compile-triggering `.cs`, then request play exit through
`exec` (`EditorApplication.isPlaying = false`) and poll `/health` until play mode is observed to end.

| Setting | stop exec | play exit observed | endpoint unreachable |
|---|---|---|---|
| `recompile_and_continue_playing` (0) | `completed` | 0.3 s | 0 s |
| `recompile_after_finished_playing` (1) | `warning` (`compile_blocked_by_play_mode`) | 57.6 s | 15.5 s |
| `stop_playing_and_recompile` (2) | `warning` (`compile_blocked_by_play_mode`) | 0.3 s | 0 s |

Result: **D6 hypothesis 2 held.** With `recompile_after_finished_playing`, the stop request returns
success at once, but the Editor then runs the deferred compile and reloads the domain; the control
endpoint is unreachable for ~15 s and the Editor does not finish leaving play mode for ~58 s. An
agent that probes right after the request sees a timeout/unreachable endpoint and reads it as
"cannot stop play mode". Hypotheses 1, 3, 4, and 5 did not reproduce.

Acted on in group 4: the play-mode guidance names this window and orders the continuation
`exec` (exit) -> `exec` (confirm play state) -> `wait-for-compile`, so an unreachable endpoint during
the reload is treated as progress rather than a failed stop.

## Real-host end-to-end case (tasks 5.2 / 5.3)

`tests.test_real_host_integration.PlayModeCompileBlockRealHostTests.test_play_mode_compile_block_then_settles_after_play_exit`
passes under `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1` against the validation host:

- enter play mode, set "recompile after finished playing", touch a real `.cs`
- `exec` -> `status: "warning"`, `warning: "compile_blocked_by_play_mode"`, `compile_blocked` with
  `reason: "play_mode"`, the probe path, and `script_changes_while_playing`
- `wait-for-compile` -> `result.status: "compile_blocked"` (returns without waiting out the appear window)
- exit play mode -> the deferred compile runs on exit (crosses a domain reload, so completion is
  confirmed by `refresh.pending` clearing to `not_pending`); `wait-for-compile` then no longer reports
  `compile_blocked`

The existing `test_play_mode_skips_refresh_and_preserves_pending_change` was updated for the new
`warning` + `compile_blocked` contract and also passes.
