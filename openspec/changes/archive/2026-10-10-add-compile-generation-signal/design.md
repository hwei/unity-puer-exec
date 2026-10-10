## Context

This change implements the recommendation of the spike
`observe-compile-across-domain-reload`. Its `design.md` holds the full validation-host
timeline and the signal comparison; the load-bearing facts are:

- A deferred play-exit compile is Unity's forced synchronous recompile. `beforeAssemblyReload`
  stops the control listener before compilation finishes, so `/health` never serves
  `compiling`; the endpoint is unreachable for the whole compile + reload (~49 s on the
  validation host) and returns already `ready`.
- `CompilationPipeline.compilationFinished` fires for it **before** the reload, and a counter
  written to `SessionState` in that handler survives the reload.
- `session_marker` and `SettledImportUtcTicks` also advance on a reload that compiled nothing,
  so they are reload epochs, not compile epochs. `refresh.pending` clears at
  `compilationFinished`, before the endpoint drops, and an excluded filesystem change (a
  script deletion) compiles while `pending` reads `not_pending`.

## Decisions

### D1. A compile generation is the signal

Add a monotonic `compileGeneration` to `UnityPuerExecServer` that is incremented in the
script-compilation-completed handler only, persisted with `SessionState`, and loaded from
`SessionState` in each domain so it resumes across the reload rather than resetting. Report it
on the ready `/health` response. Incrementing on `afterAssemblyReload` is explicitly avoided:
that is what makes the existing settle timestamp a reload epoch.

### D2. A baseline, not a status, decides the inferred settle

`wait-for-compile` accepts an optional compile-generation baseline. When the current
generation is strictly greater than the baseline it returns `compile_settled` with
`compile_observed: true` and `edge: "generation_advance"`, even when the first poll is already
`ready`. Without a baseline its behavior is unchanged. The `compile-wait` contract ("an
initial `ready` is never terminal before an edge is observed") is honored: the generation
advance is the edge.

### D3. The baseline is the caller's responsibility, and the scope is stated

The command that drives the transition (`stop`) takes the baseline in-process before posting
the exit, so no cross-invocation state is needed. A `wait-for-compile` caller passes a
baseline it captured before the transition. A caller that starts after the reload without a
baseline keeps `no_compile_observed`; the requirement states this scope rather than implying
a late call can be satisfied.

## Alternatives considered

- **Reuse `session_marker` / `SettledImportUtcTicks`.** Rejected: both are reload epochs and
  would report a compile for a reload that compiled nothing.
- **Baseline on `refresh.pending`.** Rejected: it clears at `compilationFinished` before the
  drop, and excluded changes compile while it reads `not_pending`.
- **A request-scoped settle marker.** Rejected: same reload/compile conflation, plus it needs
  state a later `wait-for-compile` does not have.

## Risks

- The generation must be read from `SessionState` on every domain load; a plain static would
  reset to zero across the reload and defeat the signal.
- A compile that never completes still advances nothing; the settle timeout path is unchanged.
