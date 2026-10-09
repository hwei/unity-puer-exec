## Why

When the Editor leaves play mode with a deferred compile (`recompile_after_finished_playing`
or `stop_playing_and_recompile`), Unity compiles the pending change and then reloads the
domain. `AssemblyReloadEvents.beforeAssemblyReload` stops the control listener, so `/health`
is unreachable for the duration of the reload. If `wait-for-compile` is invoked once the
endpoint is back, the Editor is already `ready`, the change signal has cleared, and no
`compiling` state was ever observable. The command returns `no_compile_observed`.

Observed while landing `surface-play-mode-compile-block` on the validation host: the
deferred compile ran on play exit, but `wait-for-compile` returned `no_compile_observed`
because the compile edge was hidden behind the reload. The current real-host case works
around this by confirming completion through `refresh.pending` clearing to `not_pending`
rather than through `wait-for-compile`.

This is a false negative against the command's purpose: a compile did happen, and the
caller is told none was observed. An agent that branches on `no_compile_observed` may
re-trigger a compile or read stale compile messages.

## What Changes

- Determine whether a compile that completes across a control-endpoint reload can be made
  observable to `wait-for-compile`, and by what signal.
- Candidate signals to evaluate (not commitments):
  - a monotonic compile generation / "last compile finished at" epoch reported on `/health`,
    so the CLI can tell a compile settled since a baseline it took earlier;
  - a persisted settle marker keyed to the request or to the play-exit transition;
  - a CLI-maintained baseline established before the reload (for the sequence where the CLI
    drives the play exit), which does not help a caller that starts after the reload.
- Recommend one approach with its limits, then (if the spike graduates) implement it with
  unit and real-host coverage.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `compile-wait` (provisional, only if the spike graduates): the command SHALL NOT report
  `no_compile_observed` for a compile that demonstrably completed across a reload it could
  not observe, once a reliable signal exists.

## Impact

- `cli/python/unity_puer_exec_runtime.py`: the compile-wait outcome logic.
- `packages/com.txcombo.unity-puer-exec/Editor/`: possibly a compile-epoch signal on
  `/health` or a persisted settle marker.
- `tests/test_unity_session_cli.py` and `tests/test_real_host_integration.py`.
- Related: `scan-only-import-change-signal` (pending-state model) and the play-mode
  `compile_blocked` path.

## Open Questions

- Does the pending signal clear on the reload itself, or only after the post-reload import?
  The answer decides whether a pre-reload baseline is usable.
- Is a server-side compile epoch worth a protocol field, or can the CLI infer completion
  from an existing signal (`refresh.pending` plus an observed endpoint drop)?
- Should the outcome be `compile_settled` with a note that the edge was inferred, rather
  than a new status?
