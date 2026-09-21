## 1. Measure what the watcher contributes

- [ ] 1.1 Instrument the tracker for one real-host session to record whether any watcher callback fires at all, so the removal is justified from measurement rather than from the earlier probe alone. Verify: the record states the observed callback count (expected zero on the Windows target) and does not rely on the pre-change probe.

## 2. Remove the watcher

- [ ] 2.1 Delete the `FileSystemWatcher` construction, `Watchers`, `StartWatchersLocked`, and the `Shutdown` disposal loop. Verify: no `FileSystemWatcher` type reference remains in the package.
- [ ] 2.2 Delete the callback path (`OnWatcherChanged`, `OnWatcherRenamed`, `OnWatcherError`, `AddCandidate`) and the `CandidatePaths` set. Verify: nothing in the tracker mutates state from an off-thread callback and no callback handler is wired.
- [ ] 2.3 Make `Decide` and `GetPendingState` consume the scan result directly. Verify: a compile-triggering change is still detected with no watcher present.

## 3. Remove the fallback state

- [ ] 3.1 Remove `signalValid`, `deferredSignalError`, `DrainDeferredSignalError`, and the `Unknown` pending state. Verify: the pending state type and the health mapping have no unknown branch on a ready service.
- [ ] 3.2 Remove the one-shot revalidation branch in `Decide` (the invalidation it bounded no longer exists). Verify: `Decide` returns only `compile_triggering_change`, `no_pending_change`, or `play_mode`.
- [ ] 3.3 Simplify `Install()` to restore the persisted settled-import timestamp and mark the service installed; drop the install-time baseline walk. Verify: the first decision after install still detects a change made before install.

## 4. Specs and documentation

- [ ] 4.1 Apply the spec deltas: remove `Refresh decision survives watcher failure modes` and `An invalidated signal forces one refresh, then re-establishes trust`, add the scan-only detection requirement, and drop the health `unknown` cause. Verify: `openspec validate scan-only-import-change-signal` is valid.
- [ ] 4.2 Update every doc/help/comment that describes the signal as watcher-backed with a scan fallback. Verify: a grep for the watcher as a mechanism finds no remaining product description.

## 5. Tests and validation

- [ ] 5.1 Rewrite the affected tests: remove the watcher-error real-host case and the watcher source-invariant assertions; retarget the pre-attach case to assert the scan directly; keep the settled-timestamp, extension-filter, play-mode, and diagnostics coverage. Verify: the mock suite and the real-host suite pass.
- [ ] 5.2 Re-run the real-host suite and record the result, including the first-decision scan cost after the baseline walk is dropped. Verify: the evidence states whether the warmup path regressed, and names re-warming the cache as the follow-up if it did.
