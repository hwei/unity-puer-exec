## Why

When the Editor leaves play mode with a deferred compile (`recompile_after_finished_playing`
or `stop_playing_and_recompile`), Unity runs a forced synchronous recompile and then reloads
the domain. `AssemblyReloadEvents.beforeAssemblyReload` stops the control listener before the
compile finishes, so `/health` never serves `compiling`, and the endpoint returns already
`ready` with the change signal cleared. `wait-for-compile` therefore returns
`no_compile_observed` for a compile that demonstrably happened.

The spike `observe-compile-across-domain-reload` reproduced this and rejected the existing
signals (see that change's `design.md`): `session_marker` and `SettledImportUtcTicks` are
*reload* epochs that advance on a reload which compiled nothing, and `refresh.pending` clears
at `compilationFinished` *before* the endpoint drops. A compile-specific generation is the
only reliable discriminator, and only for a caller that holds a baseline from before the
transition.

## What Changes

- **Expose a monotonic compile generation on `/health`.** The Editor increments a generation
  only when a script compilation completes (`CompilationPipeline.compilationFinished`),
  persists it in `SessionState` so it survives the domain reload, and reports it on the ready
  health response.
- **Let `wait-for-compile` settle an inferred cross-reload compile from a baseline.**
  `wait-for-compile` accepts an optional compile-generation baseline. When the current
  generation is greater than the baseline, it reports `compile_settled` with
  `compile_observed: true` even though it never saw `compiling`, and it names the edge it used
  (for example `edge: "generation_advance"`). The `compile-wait` contract is honored, not
  amended: a generation advance is an observed edge.
- **Scope the guarantee explicitly.** Only a caller that holds a baseline from before the
  reload can be satisfied. A caller that starts after the reload and supplies no baseline
  keeps `no_compile_observed`. The command that drives the transition itself (`stop` in
  `add-play-mode-commands`) takes the baseline in-process; a `wait-for-compile` caller
  passes one.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `compile-wait`: `wait-for-compile` can settle a compile inferred across a domain reload
  from a caller-supplied compile-generation baseline, and never falsely settles without one.
- `project-control-endpoint`: the ready `/health` response exposes a monotonic compile
  generation that survives a domain reload.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`: increment, persist,
  and report the compile generation.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs`: a
  `BuildHealthResponseJson` field for the generation.
- `cli/python/unity_puer_exec_surface.py`, `cli/python/unity_puer_exec_runtime.py`: the
  compile-generation baseline selector and the inferred-settle outcome in
  `wait_for_compile_cycle` / `_run_wait_for_compile_impl`.
- `tests/test_unity_session_cli.py`, `tests/test_real_host_integration.py`: unit coverage
  for the outcome and a real-host case that stages the deferred play-exit compile and
  asserts `compile_settled` from a pre-exit baseline.
- Related: `observe-compile-across-domain-reload` (the spike that produced the finding),
  `scan-only-import-change-signal` (pending-state model), `surface-play-mode-compile-block`
  (the `compile_blocked` path). `add-play-mode-commands` lists
  `observe-compile-across-domain-reload` in `blocked_by`: its `stop` command consumes the
  compile generation as the completion signal for the deferred compile it drives (its D4).
