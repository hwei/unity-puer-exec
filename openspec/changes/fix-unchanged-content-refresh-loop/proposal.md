# Proposal

## Why

`play` and every project-scoped `exec` can loop for minutes in the automatic-refresh phase
when a compile-triggering file's mtime moves but its content does not — the ordinary result
of a `git rebase`, `git reset`, or branch round-trip that rewrites a `.cs` file identically
(GitHub issue [#3](https://github.com/hwei/unity-puer-exec/issues/3)). `AssetDatabase.Refresh()`
sees an identical content hash and starts no compilation, so neither `compilationFinished` nor
`afterAssemblyReload` fires, the settled-import timestamp never advances, `Decide()` keeps
returning `compile_triggering_change`, and the CLI keeps re-dispatching a ~10 ms no-op refresh
until its budget runs out. The pending state is permanent for the life of the Editor session,
so the only operator workaround is hand-editing file mtimes.

## What Changes

- The change signal stops treating mtime alone as proof that Unity has not imported a file.
  The tracker keeps a ledger of the content it has already handed to a successfully dispatched
  `AssetDatabase.Refresh()` during the current unsettled epoch, and drops a scanned path whose
  current content matches that ledger.
- The ledger is written only after a dispatch succeeded, is keyed by path, and is cleared
  whenever the settled-import timestamp advances, so it can never suppress a content state
  Unity has not been asked to import.
- `GetPendingState()` (the `/health` view) applies the same filter as `Decide()`, so health and
  the exec decision cannot disagree about whether a change is pending.
- The refresh diagnostics block gains `paths_suppressed`, naming the paths the scan flagged by
  mtime and the content ledger then dropped. `triggered`, `reason`, `paths_changed`,
  `skipped_reason`, `settle_outcome`, and `elapsed_ms` keep their current meaning.
- No CLI behavior change and no protocol removal: a suppressed decision reports
  `triggered: false` with `skipped_reason: "no_pending_change"`, which every existing caller
  already treats as "proceed".
- The settled-import timestamp keeps its single writer and still advances only on Unity's
  completion signals. What changes is the detection side: an mtime newer than the settled
  timestamp is a candidate, not a verdict.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `import-change-refresh`: "Change detection is the incremental filesystem scan alone" gains
  the content-ledger filter and its diagnostics; "Exec responses disclose the refresh decision"
  gains `paths_suppressed`; "Repeated execs after a single change do not refresh repeatedly"
  gains the content-identical-rewrite case that issue #3 exposed. "Settled-import timestamp
  advances only on Unity completion signals" is deliberately **not** amended — the loop is fixed
  on the detection side, so that invariant stays intact.

## Impact

- **Host**: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecImportChangeTracker.cs`
  (ledger, filter, `OnRefreshDispatched`), `UnityPuerExecServer.cs` (record after a successful
  dispatch, pass suppressed paths into the block), `UnityPuerExecProtocol.cs`
  (`BuildRefreshBlockJson`).
- **CLI**: none. The refresh block is passed through verbatim by
  `cli/python/unity_puer_exec_runtime.py`.
- **Tests**: `tests/test_refresh_change_signal.py` source invariants; a package EditMode case
  for the block field; a real-host case that rewrites a probe `.cs` with identical content and
  asserts the next exec completes instead of looping.
- **Upstream**: follows `2026-09-21-refresh-on-change`, which established the mtime-versus-
  settled-timestamp signal, and `2026-09-21-diagnose-exec-missing-after-auto-refresh`, which
  established that refresh is a non-terminal phase the CLI settles and re-submits.
- **Cost**: one content read and hash per already-flagged path per decision (typically 0–3
  files), outside the tracker's lock. Unflagged trees still cost enumeration and stat only.
