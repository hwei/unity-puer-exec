## 1. Measure what the watcher contributes

- [x] 1.1 Instrument the tracker for one real-host session to record whether any watcher callback fires at all, so the removal is justified from measurement rather than from the earlier probe alone. Verify: the record states the observed callback count (expected zero on the Windows target) and does not rely on the pre-change probe.

## 2. Remove the watcher

- [x] 2.1 Delete the `FileSystemWatcher` construction, `Watchers`, `StartWatchersLocked`, and the `Shutdown` disposal loop. Verify: no `FileSystemWatcher` type reference remains in the package.
- [x] 2.2 Delete the callback path (`OnWatcherChanged`, `OnWatcherRenamed`, `OnWatcherError`, `AddCandidate`) and the `CandidatePaths` set. Verify: nothing in the tracker mutates state from an off-thread callback and no callback handler is wired.
- [x] 2.3 Make `Decide` and `GetPendingState` consume the scan result directly. Verify: a compile-triggering change is still detected with no watcher present.

## 3. Remove the fallback state

- [x] 3.1 Remove `signalValid`, `deferredSignalError`, `DrainDeferredSignalError`, and the `Unknown` pending state. Verify: the pending state type and the health mapping have no unknown branch on a ready service.
- [x] 3.2 Remove the one-shot revalidation branch in `Decide` (the invalidation it bounded no longer exists). Verify: `Decide` returns only `compile_triggering_change`, `no_pending_change`, or `play_mode`.
- [x] 3.3 Simplify `Install()` to restore the persisted settled-import timestamp and mark the service installed; drop the install-time baseline walk. Verify: the first decision after install still detects a change made before install.
- [x] 3.4 Preserve the scan's exclusion rules while removing the watcher and the baseline walk: keep the dot-directory segment test, and move the normalized watched-root cache from `StartWatchersLocked` into `Install()` so its root-relative scope survives. Verify: `Assets/.not_imported/Foo.cs` is still excluded, `F:/.work/proj/Assets/Foo.cs` is not, and the root-cache source-invariant from `root-relative-dot-directory-exclusion` in `tests.test_refresh_change_signal` still passes.

## 4. Specs and documentation

- [x] 4.1 Apply the spec deltas: remove `Refresh decision survives watcher failure modes` and `An invalidated signal forces one refresh, then re-establishes trust`, add the scan-only detection requirement, and drop the health `unknown` cause. Verify: `openspec validate scan-only-import-change-signal` is valid.
- [x] 4.2 Update every doc/help/comment that describes the signal as watcher-backed with a scan fallback. Verify: a grep for the watcher as a mechanism finds no remaining product description.

## 5. Tests and validation

- [x] 5.1 Rewrite the affected tests: remove the watcher-error real-host case and the watcher source-invariant assertions; retarget the pre-attach case to assert the scan directly; keep the settled-timestamp, extension-filter, play-mode, and diagnostics coverage. Verify: the mock suite and the real-host suite pass.
- [x] 5.2 Re-run the real-host suite and record the result, including the first-decision scan cost after the baseline walk is dropped. Verify: the evidence states whether the warmup path regressed, and names re-warming the cache as the follow-up if it did.
  - Result: the full real-host suite passes (41 tests, 3 skipped). Measurement is recorded in `results/real-host-evidence.md`. The warmup path **did** regress (contended post-reload scans produced an 8.5-13.5 s first-decision cost and a deterministic `unity_stalled`), and the named follow-up — re-warming the snapshot cache without a watcher — was implemented in `Install()` (`WarmSnapshotCache`, no change signal). A single warm walk is ~150-300 ms and the play-mode class went from failing back to 6/6 OK.

## 6. Reconcile with the shared-host real-host harness

- [x] 6.1 Update the per-case reset in `tests/test_real_host_integration.py` (introduced by the archived `reuse-real-host-editor-across-suite`) for the scan-only tracker: stop calling the `Shutdown`/`Install` members that no longer exist or no longer do that job, remove the reset branch keyed on the deleted `Unknown` pending state, and stop assuming `Install()` warms a settled baseline. Verify: the reset still leaves the tracker `not_pending`, and the refresh cases pass in any order on one reused Editor rather than a fresh launch per case.
- [x] 6.2 Retire the refresh cases and assertions this change makes false: remove `test_watcher_error_invalidates_signal_then_forces_one_refresh` (the watcher-error path and the `unknown` state it asserted) and confirm no remaining case or reset helper asserts `refresh.pending == "unknown"`. Verify: a grep for the watcher-error case and for `unknown` in the pending contract leaves nothing to maintain.
- [x] 6.3 Preserve the reload-loss regression that `diagnose-exec-missing-after-auto-refresh` adds to `test_base_url_automatic_refresh_and_wait_for_compile` while rewriting the refresh cases. Verify: that regression still runs against the scan-only tracker and is not dropped with the watcher-error coverage.
