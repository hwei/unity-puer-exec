## Context

The real-host suite is opt-in (`UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`) and runs on a
machine that provides Unity Editor and `UNITY_PROJECT_PATH`. Its reported cost is
attributable, and the attribution is the whole problem:

```
per case:
  _ensure_clean_test_boundary(project)   stop the host        ~1s
  prepare_validation_host.main(...)      wire the manifest    <1s
  cleanup_validation_temp_assets(...)    reset fs state       <1s
  _warm_up_project_exec(...)             launch + import      ~60-90s   <-- dominant
  <assertions>                                                 seconds
```

The launch is not per-case *work*; it is per-case *setup*, and it exists only to give
each case a process and filesystem it did not share with the previous case. Two facts
make that cost avoidable, given the properties the current model actually relies on:

1. The clean-boundary check is already the suite's real isolation primitive. Cases do
   not assume a virgin Unity process; they assume a host brought up by the suite and a
   project free of repository-owned leftovers. That is a filesystem and lifecycle
   property, not a process-identity property.
2. The cases that *do* need process identity are few and already self-contained: the
   batch-mode activation cases launch their own one-shot `Unity.exe` processes, and the
   port-rollover case stages its own occupy-then-rebind condition. They do not use the
   shared interactive host for the property under test.

`ValidationHostRealHostTests` (the older class) and `RefreshOnChangeRealHostTests` both
relaunch per case today.

## Goals / Non-Goals

**Goals:**

- Bring the host up once per suite and let ordinary cases reuse it.
- Keep the per-case isolation the current model provides, via explicit state reset.
- Preserve the transient cold-launch retry and the machine-usable failure diagnostics.
- Keep pristine-process cases possible without weakening their property.

**Non-Goals:**

- No product behavior change, in the Editor package or the CLI.
- No change to the opt-in gate, the project-path selector, the host-private log model,
  or the boundary rules for lockfile and published endpoint.
- No parallelism. Cases still run sequentially against one host.

## Decisions

### Decision 1: A class-level fixture owns the host lifecycle

Each real-host class gains a `setUpClass` that (a) confirms the clean boundary and
brings the host up through the existing `real_host_retry.warm_up_with_retry` path, and
(b) records the resolved `base_url`. `tearDownClass` stops the host and removes
repository-owned validation temp assets. `tearDownClass` runs even when a case fails, so
a failing case cannot leave a running Editor behind for the next suite invocation.

`setUp` keeps only the cheap per-case reset (see Decision 2); it no longer stops or
relaunches anything.

The existing helper chain is reused, not replaced: `_ensure_clean_test_boundary`,
`prepare_validation_host`, `cleanup_validation_temp_assets`, and `_warm_up_project_exec`
already are the pieces the fixture needs, and each is already unit-or-real tested.

### Decision 2: Isolation is explicit state reset, not process identity

A shared process is only unsafe if a case can observe the previous case's state. The
suite already removes repository-owned validation temp assets per case; the reuse model
adds the other state a shared process can carry:

- **Editor play mode.** A case that enters play mode must not leave it playing. The
  per-case reset asserts the Editor is out of play mode and leaves it so, so a following
  case does not run against a play-mode host.
- **Change-signal state.** The refresh tests deliberately leave candidates and a
  synthetic pending change in the tracker. The per-case reset clears repository-owned
  candidates and re-settles the signal so the next case starts from `not_pending`.
- **Filesystem.** Validation temp assets (including any probe subdirectories) are
  removed per case; the boundary check confirms no stale host state is being observed.

This is what the current per-case relaunch achieves as a side effect. Making it explicit
is the point: a reused host must reset what it reuses, and the reset is now a named,
tested step rather than an implicit consequence of process death.

### Decision 3: Pristine-process cases opt out, visibly

A case that needs a process the shared host cannot be — the batch-mode activation cases
and the port-rollover case — keeps its own launch/stop and reports its boundary result.
It does not silently run on the shared host and then assert a property that host cannot
have. The opt-out is a named fixture on the case, not an ad-hoc stop mid-suite, so a
future reader can see which cases are intentionally outside the reuse model.

### Decision 4: Failure semantics are unchanged

The reuse model changes *when* a launch happens, not what counts as a launch failure.
`real_host_retry.warm_up_with_retry` still retries only transient cold-launch failures
(`unity_start_failed`, or an Editor that exits before ready) within a bounded budget and
still refuses to retry assertion failures. A shared host that dies mid-suite is detected
by the case's own health/base-url resolution (the same `_scan_ready_control_endpoint`
oracle) and either re-established or failed with the recorded attempt state.

## Risks / Trade-offs

**[A case leaks state into the next case]** → The reset in Decision 2 targets exactly the
state a shared process carries across cases; the isolation scenarios in the spec are the
acceptance test. The failure mode is a flaky next case, which is worse than a slow suite,
so the reset is explicit and reviewed rather than assumed.

**[A suite-level launch failure loses per-case retry granularity]** → The retry budget is
applied at the suite level: one bounded retry of the host launch, and cases fail with the
suite's launch diagnostics. This trades a little retry granularity for not paying for it
ten times. If evidence shows a per-case launch was masking a transient per-case failure,
the retry can move back without changing the spec.

**[A case genuinely needs a fresh process but is not recognized as one]** → The opt-out in
Decision 3 is explicit; a case that later discovers it needs a pristine process adds the
opt-out and says why. The default is the shared host, and a shared-host case that fails
only on reuse is evidence for the opt-out, not evidence against the model.

**[Wall-clock improvement is assumed rather than measured]** → The change measures the
suite's wall-clock before and after and records it. If the host relaunch was not the
dominant cost, the change's premise is wrong and the record must say so.

## Migration Plan

1. Add the class-level fixture and the per-case reset to `RefreshOnChangeRealHostTests`
   first (it is the largest class and has the richest shared state: temp assets, play
   mode, synthetic pending changes).
2. Move `ValidationHostRealHostTests` onto the same fixture once the reset is proven.
3. Give the pristine-process cases their explicit opt-out.
4. Run the full real-host suite on the shared host; record wall-clock and any case that
   relied on the old per-case relaunch.
5. Update `how-to-run.md` with the reuse model and the isolation guarantees.

Rollback: revert the fixtures to per-case relaunch. The specification delta is the only
durable artifact; the harness shape is otherwise internal.
