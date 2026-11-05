# Tasks

## 1. Tracker content ledger

- [ ] 1.1 Add the per-path content ledger to `UnityPuerExecImportChangeTracker` (path → content
      hash handed to a dispatched refresh since the timestamp last advanced), guarded by the
      existing `Gate`, and clear it inside `OnCompilationCompleted()` before the timestamp is
      persisted. Verify: `python -m unittest tests.test_refresh_change_signal` passes with the
      new invariant assertions from 3.1.
- [ ] 1.2 Split the scan from the filter: keep `ScanWatchedRoots()` returning mtime candidates,
      add a shared helper that hashes each candidate's content outside the lock and drops the
      ones matching the ledger, treating an unreadable candidate as never suppressed. Verify:
      `Decide()` and `GetPendingState()` both return the filtered set, and
      `python -m unittest tests.test_refresh_change_signal` passes.
- [ ] 1.3 Carry the decision's inputs out for recording: `RefreshDecision` gains the suppressed
      paths and the `(path, content hash)` pairs behind `PathsChanged`, captured before the
      dispatch, plus `OnRefreshDispatched(RefreshDecision)` that writes them into the ledger.
      Verify: `python -m unittest tests.test_refresh_change_signal` passes with the
      record-only-after-dispatch assertion from 3.1.

## 2. Server dispatch and disclosure

- [ ] 2.1 Call `UnityPuerExecImportChangeTracker.OnRefreshDispatched(decision)` in
      `EvaluateRefreshAsync` only on the branch where `AssetDatabase.Refresh()` returned without
      throwing, so `settle_outcome: "failed"` records nothing. Verify:
      `python tools/preflight_compile_check.py` reports `status: ok` against the validation host.
- [ ] 2.2 Add `paths_suppressed` to `UnityPuerExecProtocol.BuildRefreshBlockJson` and pass the
      decision's suppressed paths from both the triggered and skipped branches of
      `EvaluateRefreshAsync`. Verify: `python tools/preflight_compile_check.py` reports
      `status: ok`, and the EditMode case from 3.2 passes.

## 3. Repository test layer

- [ ] 3.1 Extend `tests/test_refresh_change_signal.py` with the ledger's structural invariants:
      the timestamp still has a single writer, the ledger is cleared inside
      `OnCompilationCompleted()`, `Decide()` and `GetPendingState()` both apply the filter, and
      the ledger is written only from `OnRefreshDispatched`. Verify:
      `python -m unittest tests.test_refresh_change_signal` passes.
- [ ] 3.2 Add a package EditMode case asserting `BuildRefreshBlockJson` emits
      `paths_suppressed` (populated and empty) alongside the six existing keys. Verify:
      `python tools/run_editmode_tests.py` reports `status: passed` with the new case counted in
      `total`.
- [ ] 3.3 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.

## 4. Real-host validation

- [ ] 4.1 Add a real-host case to `RefreshOnChangeRealHostTests` that writes a probe `.cs`, lets
      it settle, rewrites it byte-identically so only its mtime moves, and asserts the next
      `exec` reaches `completed` in one invocation and a following `exec` reports
      `triggered: false`. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.RefreshOnChangeRealHostTests`
      passes against the host in `.env`.
- [ ] 4.2 Add a real-host case for the disclosure and the health view: after the identical
      rewrite is suppressed, the exec response names the path in `paths_suppressed` and `/health`
      reports `pending: "not_pending"`. Verify: the same command as 4.1 passes.
- [ ] 4.3 Reproduce issue #3's report end to end on the validation host: with the Editor settled,
      `touch` a tracked `.cs` under `Assets/` without changing its content, then run
      `unity-puer-exec play --project-path <host>` and record that it reaches
      `play_state: "playing"` instead of expiring its budget in `phase: "refreshing"`. Verify: the
      transcript is captured in the change directory or the closeout summary.

## Workflow follow-up

- Archive the change with `openspec archive fix-unchanged-content-refresh-loop` once the
  real-host evidence is recorded and the review requirements are satisfied.
- Close issue #3 against the released package version that carries the fix.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
