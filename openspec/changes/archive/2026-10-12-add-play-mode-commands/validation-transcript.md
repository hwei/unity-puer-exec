# Validation Transcript — add-play-mode-commands

## Real-host command cases (task 5.1)

Command:

```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest \
  tests.test_real_host_integration.PlayModeCompileBlockRealHostTests -v
```

Result: `Ran 6 tests in 737.291s` — `OK`.

```
test_deferred_play_exit_compile_settles_from_a_generation_baseline ... ok
test_play_aborts_on_a_compile_error_without_entering_play_mode ... ok
test_play_mode_compile_block_then_settles_after_play_exit ... ok
test_play_pause_play_resumes_against_real_host ... ok
test_play_settles_a_pending_change_then_reaches_playing ... ok
test_stop_settles_the_deferred_compile_against_real_host ... ok
```

The cases assert `play` pre-settles a pending `.cs` change and discloses the refresh,
`play`/`pause`/`play` reaches `playing`/`paused`/`playing` (`transition: resumed`),
`stop` leaves edit mode and reports `compile.outcome: compile_settled` with
`edge: generation_advance` for the play-exit deferred compile, and `play` aborts with
`unity_compile_error` (exit 23) without ever posting `/play-mode` for a broken build.

## Run-in-background confirmation (task 5.2)

Probes: `.tmp/play_mode_run_in_background_probe.py` and
`.tmp/play_mode_run_in_background_negative_probe.py`, run against the validation host
with the Editor not the focused window.

`PlayerSettings.runInBackground` was `true` on the host. For the negative case the probe
temporarily set it to `false` through an explicit `exec`, measured, and restored it. The
host's `git diff -- Project/ProjectSettings/ProjectSettings.asset` is empty, so the
product never wrote the asset — only the explicit probe write, restored to its committed
value.

Forced play (default), project setting `false`:

| observation | value |
|---|---|
| `result.run_in_background.forced` | `true` |
| `result.run_in_background.project_setting` | `false` |
| `Application.runInBackground` in play mode | `true` |
| `Time.frameCount` delta over 6 s | 6452 |

`play --no-run-in-background`, project setting `false`:

| observation | value |
|---|---|
| `result.run_in_background.forced` | `false` |
| `result.run_in_background.project_setting` | `false` |
| `Application.runInBackground` in play mode | `false` |
| `Time.frameCount` delta over 6 s | 83 |

Conclusion:
- A forced play session keeps advancing frames while the Editor is unfocused
  (≈1075 frames/s).
- Without the override, the unfocused Editor is heavily throttled (≈14 frames/s).
- `ProjectSettings.asset` is unchanged.
- **Interaction Mode throttling is preserved, by design.** With the override off, the
  loop did not fully stall; it advanced ~83 frames in 6 s. That is the Editor's
  unfocused Interaction Mode throttle, a separate setting from `runInBackground`.

## Disposition (human-reviewed)

- The Interaction Mode throttle is Unity's own native behavior and is intentionally
  left in place. `--no-run-in-background` keeps the project's setting and therefore
  keeps Unity's original throttling; the default `play` only forces
  `Application.runInBackground` for the session it starts.
- Decision: do not add a follow-up to make an unfocused Editor fully stop. There is no
  validation gap to close here.

