# refresh-on-change — signal/timestamp task evidence (2026-09-20, follow-up session)

Continues `real-host-evidence-20260920.md`. That session made the scan the real change
signal and the loop-breaking property pass. This session closed the remaining tasks:
2.1, 2.2, 3.2–3.5, 4.2, 4.4, and the 7.4 archive-readiness review.

Environment: validation host `tree2` (`UNITY_PROJECT_PATH`), Unity 2022.3.62f2,
repository package wired via manifest (`embedded_package_shadowing: false`), host
launched by the suite (isolated `-logFile`). `tree2` has Enter Play Mode domain reload
**disabled** (`m_EnterPlayModeOptions: 3`), so the play-mode cases do not cross a
domain reload.

## Implementation changes

1. **Removed every `[UPE-DIAG]` log from the tracker.** The logs included the watcher
   callbacks, whose entire contract is that they touch no Unity API from a threadpool
   thread. The error diagnostic is now recorded as plain state
   (`deferredSignalError`) inside the callback and emitted by `DrainDeferredSignalError`
   on the next request/main-thread access.
2. **Made the error fallback one-shot, and specified it.** With the scan as the
   authoritative signal source, a permanently invalid `signalValid` would force a
   refresh on every exec and never clear (no compilation would fire a completion
   hook). `Decide()` now re-establishes trust after its own successful scan: the first
   exec after an invalidation refreshes once with `reason: watcher_signal_unavailable`,
   and the next is an ordinary no-change decision. `/health` still reports `unknown`
   until that decision consumes the invalidation. This is now a requirement
   (`import-change-refresh / An invalidated signal forces one refresh, then
   re-establishes trust`) rather than only a design note.

## New coverage

`tests/test_real_host_integration.py` → `RefreshOnChangeRealHostTests` (10 cases, all
passing; `Ran 10 tests in 906.402s ... OK`). New cases:

| Task | Case | Observable |
|---|---|---|
| 2.1 | `test_settled_timestamp_survives_domain_reload` | live field == persisted `SessionState`; forced reload → health `not_pending`, next exec `triggered:false`; `Shutdown()`+zero field+planted persisted value → `Install()` restores exactly that value |
| 2.2 | `test_exec_and_refresh_do_not_advance_settled_timestamp` | exec leaves ticks unchanged; explicit `AssetDatabase.Refresh()` with nothing to compile leaves ticks unchanged |
| 3.2 | `test_non_code_writes_do_not_mark_dirty` | `.unity`, `.prefab`, `.meta`, `.png`, `.wav` writes each leave health `not_pending`; next exec `triggered:false` |
| 3.4/4.4 | `test_watcher_error_invalidates_signal_then_forces_one_refresh` | health `unknown`; next exec `triggered:true`, `reason:watcher_signal_unavailable`, script still runs; then health `not_pending` and a plain no-change exec |
| 3.5 | `test_change_made_before_install_is_caught_by_baseline_walk` | `Shutdown()` → write `.cs` → `Install()` → pending state `Pending` in-process and on `/health` |
| 4.2/4.4 | `test_play_mode_skips_refresh_and_preserves_pending_change` | health `pending` + `suppressed`/`suppressed_reason:play_mode`; exec `triggered:false`, `skipped_reason:play_mode`, script runs; signal still `pending` after the skip; first exec after play exit `triggered:true`, `reason:compile_triggering_change` |

The internal tracker has no control-endpoint surface for its raw state, so the new
cases reach it through the Editor's own JS environment by reflection
(`puer.loadType` + `AppDomain` + `BindingFlags`). This is a white-box probe of the same
static state the server uses, not a stub: the decision logic and health surface under
assertion are the real ones.

Source-level invariants (task 3.3, and the parts of 3.4/3.5 that cannot be produced
from outside on Windows) are pinned in `tests/test_refresh_change_signal.py` (8 cases):
callback path touches no Unity API, candidate set is a case-insensitive `HashSet`
mutated only under `Gate`, handlers funnel through `AddCandidate`, `OnWatcherError`
sets `signalValid=false`, the timestamp has a single writer, `Install()` runs the
baseline walk, and the completion hook clears candidates and revalidates the signal.

## Totals

- Mocked suite: `Ran 483 tests ... OK` (475 previous + 8 new source-invariant cases).
- Real-host `RefreshOnChangeRealHostTests`: `Ran 10 tests ... OK` (4 previous + 6 new).
- `openspec validate refresh-on-change`: `Change 'refresh-on-change' is valid`.
- `openspec status --change refresh-on-change --json`: `isPlanningComplete: true`,
  `isComplete: true`, all artifacts `done`.

## Archive readiness (7.4)

- All 26 tasks complete.
- Every spec delta has a corresponding implementation: `import-change-refresh`
  (tracker + decision + one-shot invalidation fallback + diagnostics/tests),
  `project-control-endpoint` (health refresh block), `compile-error-surface` (removed
  flag field + gate ordering), `exec-import-support`, `formal-cli-contract` (CLI
  refresh handling), `runtime-guidance` (help rewrites).
- The new capability's Purpose is written; no `TBD` Purpose placeholder was introduced
  by this change (the existing `TBD` Purposes are pre-existing durable specs unrelated
  to this change).
- No `[UPE-DIAG]` diagnostic logs remain in the package.
