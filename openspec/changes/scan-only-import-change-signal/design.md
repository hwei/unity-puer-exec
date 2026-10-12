## Context

`refresh-on-change` shipped two signal producers: a per-root `FileSystemWatcher` and an
incremental directory scan. The change's evidence recorded the measurement that decided
the relationship between them: in Unity Editor's embedded Mono on Windows, the watcher
binds, reports `EnableRaisingEvents == true`, and delivers zero callbacks; the same
watcher outside the editor fires immediately. Later sessions saw raw events arrive
delayed and unreliably, never deterministically. The scan was therefore made the real
signal and the watcher was kept as an accelerator.

That decision was correct at the time and is the reason the feature works. What it left
behind is a subsystem whose only input never arrives. Everything downstream of "a watcher
can fail" — an error handler, an invalidity flag, an unknown health state, a deferred
diagnostic, a one-shot revalidation rule, and two spec requirements — exists to make a
watcher safe. None of it detects a change.

The tracker's existing shape, for reference:

```
Decide() / GetPendingState()
  scan roots -> found (paths newer than settle_ticks)      <- the real signal
  merge watcher-delivered CandidatePaths                   <- never populated here
  changed = candidates newer than settle_ticks
  if !installed || !signalValid -> Unknown / forced refresh <- watcher-only failure path
```

## Goals / Non-Goals

**Goals:**

- Make the scan the only change-detection mechanism, in code and in the specs.
- Remove the watcher, its callbacks, its thread-safety audit surface, and the fallback
  state that existed only because a watcher can fail.
- Keep every behavior the fallback was standing in for: pre-attach changes, changes
  across a domain reload, and the settled-timestamp semantics.

**Non-Goals:**

- No change to the settled-import timestamp contract, the extension filter, the play-mode
  skip, the refresh diagnostics block for ordinary decisions, or the CLI.
- No attempt to make a watcher work on Unity's embedded Mono, and no cross-platform
  watcher support (macOS/Linux are out of scope for this repository).

## Decisions

### Decision 1: Delete the watcher; the scan is the signal

The scan already satisfies the correctness property the watcher was supposed to assist:
every decision walks the watched roots and compares modification times against the
settled-import timestamp. It is inherently immune to the two gaps the watcher fallback
compensated for — a change made before attach and a change made across a domain reload —
because it holds no in-memory event state to lose and re-reads the filesystem each time.

So the watcher, `Watchers`, `StartWatchersLocked`, `OnWatcherChanged`,
`OnWatcherRenamed`, `OnWatcherError`, `AddCandidate`, and the `CandidatePaths` set they
fed are removed. `Decide` and `GetPendingState` use the scan's `found` list directly.

### Decision 2: Delete the failure-state machinery with it

`signalValid`, `deferredSignalError`, `DrainDeferredSignalError`, the `Unknown` pending
state, and the one-shot revalidation rule exist only to describe and bound watcher
failure. With no watcher there is no invalidation, so they are removed rather than kept as
unreachable branches. A ready service answers `pending` or `not_pending`.

### Decision 3: The install-time baseline walk goes with the mechanism it demoted

The baseline walk was the fallback for "changed before the watcher attached". When every
decision scans, a separate install-time walk is redundant: the first decision after
install sees the same filesystem. `Install()` keeps only its real job — restoring the
persisted settled-import timestamp and marking the service installed.

Accepted consequence: the snapshot cache is no longer warmed at install, so the first
decision pays the cold scan cost that the warmup exec already absorbs today (the change's
evidence recorded ~9-11s cold, ~0.3-0.8s warm). If measurement shows this regressing the
warmup path, re-warming the cache without a watcher is the follow-up, not a reason to
keep the watcher.

### Decision 4: The specs describe the mechanism that exists

Removing the watcher means two requirements become false descriptions of the system:

- `Refresh decision survives watcher failure modes` — no watcher, no failure modes.
- `An invalidated signal forces one refresh, then re-establishes trust` — no invalidation.

Both are REMOVED, replaced by a scan-only detection requirement that keeps their testable
guarantees (pre-attach detection, reload-independence) without the watcher premise. The
health requirement drops its `unknown` cause for the same reason: an unreachable degraded
state in a contract is a lie a future reader will believe.

### Decision 5: Reconcile with the real-host reuse harness, not just with the tracker

The real-host suite no longer relaunches the Editor per case.
`reuse-real-host-editor-across-suite` (archived 2026-09-21) made each class bring one
Editor up and reset test-owned state between cases, and its per-case reset in
`tests/test_real_host_integration.py` reaches into this tracker through reflection:

```
invokeTracker('Shutdown')
invokeTracker('Install')
invokeTracker('OnCompilationCompleted')
```

and its fast path reads `health.refresh.pending == "not_pending"` to decide whether the
tracker needs re-settling at all.

Those touch points are exactly what this change removes or reshapes:

- `Shutdown`'s job in the reset was to drop watcher-fed candidates and reinstall. With
  `CandidatePaths` gone, that call is at best a no-op and at worst a missing member.
- The `Unknown` pending state the reset falls back on no longer exists, so any reset
  branch keyed on it is dead.
- The reset relied on the install-time baseline walk to establish the settled baseline
  for a case. Decision 3 removes that walk, so the reset must not assume a warm baseline.

So this change owns the reconciliation of the shared-host reset with the scan-only
tracker. It is not optional cleanup: leaving the reset calling into deleted members
breaks every refresh case in the suite during `setUp`, and leaving it asserting `unknown`
asserts a state the contract no longer has.

This change also rewrites the refresh real-host cases — the same surface where
`diagnose-exec-missing-after-auto-refresh` adds its reload-loss regression (the
deterministic `test_base_url_automatic_refresh_and_wait_for_compile` failure). That
change has landed (archived 2026-09-21), so the rewrite must preserve its regression
rather than drop it alongside the watcher-error case.

## Risks / Trade-offs

**[A future platform wants a watcher]** → Out of scope by explicit decision; macOS/Linux
are not targets. If that changes, re-introducing a watcher is an additive change against
the scan-only requirement, not a revert of this one.

**[Removing the candidate set leaves the scan as the only producer, and a scan bug is now
unmitigated]** → The candidate set never contained anything the scan did not also find,
so it was not an independent mitigation. The scan's correctness rests on the mtime
comparison and the settled-import timestamp, which are unchanged and covered by real-host
cases.

**[Removing the watcher drops the scan's exclusion scope]** → The dot-directory test
(`ignore-dot-directories-in-import-change-scan`) and its root-relative scope
(`root-relative-dot-directory-exclusion`, which caches roots in `StartWatchersLocked`)
are scan behavior, not watcher behavior. The root cache moves into `Install()`; task 3.4
and the root-relative source invariant guard it.

**[Cold scan cost moves to the first decision]** → Measured, accepted (Decision 3), with a
named follow-up if the warmup path regresses.

**[The spec removals lose a documented guarantee]** → The guarantees are re-stated in the
scan-only requirement; only the watcher premise is dropped. The real-host cases that
proved pre-attach detection (`test_change_made_before_install_is_caught_by_baseline_walk`)
and non-code filtering are rewritten to assert the scan directly, so the guarantee stays
tested.

**[The shared-host per-case reset is coupled to the tracker members this change deletes]**
→ The reset from `reuse-real-host-editor-across-suite` calls
`Shutdown`/`Install`/`OnCompilationCompleted` by reflection and reads the
`not_pending`/`unknown` pending contract. Test task 6.1 reconciles it. The failure mode if
skipped is loud rather than subtle: the whole refresh class errors in `setUp`, because the
reset runs before every case against a reused Editor.

## Migration Plan

1. Remove the watcher and its callbacks from the tracker; make `Decide`/`GetPendingState`
   consume the scan result and return `pending`/`not_pending`.
2. Remove `signalValid`, the deferred diagnostic, the `Unknown` state, the one-shot
   revalidation, and the baseline walk; simplify `Install()`.
3. Update the health mapping in `UnityPuerExecServer.cs` to the two-state contract.
4. Rewrite the affected tests: drop the watcher-error real-host case and the watcher
   source-invariant assertions; keep and retarget the scan cases; keep the settled
   timestamp, extension-filter, play-mode, and diagnostics coverage. Reconcile the
   shared-host per-case reset with the scan-only tracker (Decision 5) in the same pass,
   and preserve the reload-loss regression from `diagnose-exec-missing-after-auto-refresh`.
5. Update the run/help documentation that mentions a watcher; re-run the mock suite and
   the real-host suite and record the result.

Rollback: restore the watcher and the fallback state from the archived change; the spec
deltas invert cleanly.
