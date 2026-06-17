## 1. wait-for-compile command surface

- [ ] 1.1 Add a `wait-for-compile` subparser in `unity_puer_exec_surface.py` following the existing wait-command pattern (`_add_selector_args` + bounded timeout args), with a separate bounded appear-window control distinct from the settle timeout.
- [ ] 1.2 Route the new command through `runtime.run_cli` dispatch.

## 2. Edge-aware compile-wait primitive

- [ ] 2.1 Implement the edge-aware state machine in the runtime: poll `/health`; within the appear window wait for `compiling` (or detect compile already in progress); then settle until `ready`.
- [ ] 2.2 Return a distinct non-error `no_compile_observed` outcome when no compile appears within the appear window and none is in progress, separate from a completed compile cycle.
- [ ] 2.3 Return a non-terminal running/timeout result when an observed compile does not return to `ready` before the settle timeout.
- [ ] 2.4 Support both selectors: base-url polls the supplied endpoint directly (no identity/launch); project-path resolves via the normal project-scoped discovery path.
- [ ] 2.5 Tolerate transient connection failures during domain reload as "still in progress" until the ready/timeout boundary.

## 3. Relax refresh-before-exec to base-url

- [ ] 3.1 Remove the `validate_project_mode_only(selector, "refresh-before-exec", ...)` guard so base-url callers may use `--refresh-before-exec`.
- [ ] 3.2 Add a base-url post-refresh settle path (same-endpoint re-probe) analogous to `_ensure_project_session_ready_after_refresh`, reusing the compile-wait primitive.
- [ ] 3.3 Wire refresh-before-exec in both selectors as refresh → compile-settle → execute, so the user script runs after settle in base-url mode just as in project mode.

## 4. Non-terminal phase clarity

- [ ] 4.1 Ensure the intermediate refreshing/compiling state is surfaced as non-terminal with an explicit continuation hint, and that the terminal response carries the script result rather than `{refreshed: true}`.
- [ ] 4.2 Update help/lifecycle text to explain refresh starts an async compile, that `wait-for-compile` bridges the race, and the `RequestScriptCompilation()` vs `AssetDatabase.Refresh()` trade-off.

## 5. Tests

- [ ] 5.1 Unit coverage for the edge-aware state machine: compiling-appears-then-ready, compile-already-in-progress, no-compile-observed, and settle-timeout.
- [ ] 5.2 Unit coverage for refresh-before-exec in base-url mode running the user script after settle.
- [ ] 5.3 Real-host regression for the base-url refresh-before-exec compile loop and the stale-error race per the validation-host run instructions (evidence target: host-validation).

## 6. Closeout

- [ ] 6.1 Verify each `compile-wait` and modified `formal-cli-contract` scenario is exercised by a test or host-validation step.
- [ ] 6.2 Run the repository test suite and capture host-validation evidence; record results.
- [ ] 6.3 Produce the apply closeout finding summary and recommend the commit / `openspec archive` / final commit sequence.
