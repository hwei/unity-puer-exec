## 1. Server: monotonic compile generation

- [x] 1.1 Add a compile generation to the Unity control service that increments only when a script compilation completes, and persist it in `SessionState` so it survives a domain reload. Verify: a source-level check that the increment is on the compilation-completed event only (not on `afterAssemblyReload`), and that the value is loaded from `SessionState` in each domain.
- [x] 1.2 Report the compile generation on the ready `/health` response. Verify: `BuildHealthResponseJson` carries the field and the existing health contract tests still pass.
- [x] 1.3 Add unit coverage for the generation field and its persistence contract. Verify: the new tests fail if the field or the `SessionState` load is removed.

## 2. CLI: settle an inferred cross-reload compile

- [x] 2.1 Add an optional compile-generation baseline selector to `wait-for-compile`. Verify: the parser accepts it, and the command still functions without it.
- [x] 2.2 Extend `wait_for_compile_cycle` / `_run_wait_for_compile_impl`: when the current generation exceeds the baseline, return `compile_settled` with `compile_observed: true` and name the generation-advance edge, even when the first poll is already `ready`. Verify: without a baseline the existing `no_compile_observed` behavior is unchanged.
- [x] 2.3 Add unit tests for the three `compile-wait` delta scenarios (baseline advanced, no baseline after reload, baseline already current). Verify: `python -m unittest tests.test_unity_session_cli` passes.

## 3. Real-host validation

- [x] 3.1 Add a real-host case that stages the deferred play-exit compile, takes a compile-generation baseline before the exit, and asserts `wait-for-compile` reports `compile_settled` with the inferred edge after reconnection, and `no_compile_observed` without a baseline. Verify: the case passes under `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1` against the validation host.
