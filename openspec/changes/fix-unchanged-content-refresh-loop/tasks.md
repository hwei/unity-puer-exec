# Tasks

## 1. Tracker content ledger

- [x] 1.1 Add the per-path content ledger to `UnityPuerExecImportChangeTracker` (path → content
      hash handed to a dispatched refresh since the timestamp last advanced), guarded by the
      existing `Gate`, and clear it inside `OnCompilationCompleted()` before the timestamp is
      persisted. Verify: `python -m unittest tests.test_refresh_change_signal` passes with the
      new invariant assertions from 3.1.
- [x] 1.2 Split the scan from the filter: keep `ScanWatchedRoots()` returning mtime candidates,
      add a shared helper that hashes each candidate's content outside the lock and drops the
      ones matching the ledger, treating an unreadable candidate as never suppressed. Verify:
      `Decide()` and `GetPendingState()` both return the filtered set, and
      `python -m unittest tests.test_refresh_change_signal` passes.
- [x] 1.3 Carry the decision's inputs out for recording: `RefreshDecision` gains the suppressed
      paths and the `(path, content hash)` pairs behind `PathsChanged`, captured before the
      dispatch, plus `OnRefreshDispatched(RefreshDecision)` that writes them into the ledger.
      Verify: `python -m unittest tests.test_refresh_change_signal` passes with the
      record-only-after-dispatch assertion from 3.1.

## 2. Server dispatch and disclosure

- [x] 2.1 Call `UnityPuerExecImportChangeTracker.OnRefreshDispatched(decision)` in
      `EvaluateRefreshAsync` only on the branch where `AssetDatabase.Refresh()` returned without
      throwing, so `settle_outcome: "failed"` records nothing. Verify:
      `python tools/preflight_compile_check.py` reports `status: passed` against the validation
      host.
- [x] 2.2 Add `paths_suppressed` to `UnityPuerExecProtocol.BuildRefreshBlockJson` and pass the
      decision's suppressed paths from both the triggered and skipped branches of
      `EvaluateRefreshAsync`. Verify: `python tools/preflight_compile_check.py` reports
      `status: passed`, and the EditMode case from 3.2 passes.

## 3. Repository test layer

- [x] 3.1 Extend `tests/test_refresh_change_signal.py` with the ledger's structural invariants:
      the timestamp still has a single writer, the ledger is cleared inside
      `OnCompilationCompleted()`, `Decide()` and `GetPendingState()` both apply the filter, and
      the ledger is written only from `OnRefreshDispatched`. Verify:
      `python -m unittest tests.test_refresh_change_signal` passes.
- [x] 3.2 Add a package EditMode case asserting `BuildRefreshBlockJson` emits
      `paths_suppressed` (populated and empty) alongside the six existing keys. Verify:
      `python tools/run_editmode_tests.py` reports `status: passed` with the new case counted in
      `total`.
- [x] 3.3 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.

## 4. Real-host validation

- [x] 4.1 Add a real-host case to `RefreshOnChangeRealHostTests` that writes a probe `.cs`, lets
      it settle, rewrites it byte-identically so only its mtime moves, and asserts the next
      `exec` reaches `completed` in one invocation and a following `exec` reports
      `triggered: false`. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.RefreshOnChangeRealHostTests`
      passes against the host in `.env`.
- [x] 4.2 Add a real-host case for the disclosure and the health view: after the identical
      rewrite is suppressed, the exec response names the path in `paths_suppressed` and `/health`
      reports `pending: "not_pending"`. Verify: the same command as 4.1 passes.
- [x] 4.3 Reproduce issue #3's report end to end on the validation host: with the Editor settled,
      `touch` a tracked `.cs` under `Assets/` without changing its content, then run
      `unity-puer-exec play --project-path <host>` and record that it reaches
      `play_state: "playing"` instead of expiring its budget in `phase: "refreshing"`. Verify: the
      transcript is captured in the change directory or the closeout summary.

## 5. Suppression gates found by real-host validation (design D7)

- [x] 5.1 Age-gate suppression: a ledger entry records its dispatch instant and suppresses a
      candidate only once it is at least `PostRefreshSettleGraceTicks` old, with the constant
      kept under the CLI's compile-appear budget. Verify:
      `python -m unittest tests.test_refresh_change_signal` passes, including
      `test_grace_is_shorter_than_the_cli_compile_appear_window`.
- [x] 5.2 Activity-gate suppression: sample `EditorApplication.isCompiling || isUpdating` into a
      tracker volatile from the server's update tick before it drains the action queue, and
      refuse suppression while it is set, so both the main-thread decision and the
      listener-thread pending view gate on one snapshot. Verify:
      `python -m unittest tests.test_refresh_change_signal` passes, including
      `test_editor_activity_is_sampled_on_the_update_tick` and
      `test_suppression_is_gated_on_grace_and_editor_activity`.
- [x] 5.3 First dispatch wins: `OnRefreshDispatched` keeps an existing record whose content hash
      is unchanged, so a caller re-asking inside the bounded age cannot push it out again.
      Verify: `python -m unittest tests.test_refresh_change_signal` passes, including
      `test_a_redispatch_does_not_extend_the_grace_window`.
- [x] 5.4 Re-verify against the host: `python tools/preflight_compile_check.py` reports a
      passing compile, and both
      `tests.test_real_host_integration.PlayModeCompileBlockRealHostTests` (which caught the
      regression) and `tests.test_real_host_integration.RefreshOnChangeRealHostTests` pass under
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`.

## Workflow follow-up

- Archive the change with `openspec archive fix-unchanged-content-refresh-loop` once the
  real-host evidence is recorded and the review requirements are satisfied.
- Close issue #3 against the released package version that carries the fix.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
