# scan-only-import-change-signal — real-host evidence (2026-10-12)

Host: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
Editor: Unity 2022.3.62f2 (Hub), embedded-Mono Windows target.
Recipe: `openspec/specs/validation-host-integration/how-to-run.md`.

## Task 1.1 — watcher callback measurement (pre-removal)

The shipped watcher-backed tracker was temporarily instrumented with a
`watcherCallbackCount` incremented at the top of `OnWatcherChanged`,
`OnWatcherRenamed`, and `OnWatcherError` (before the extension filter). A file was
written under `Assets/__codex_validation_temp/not_imported~` (Unity ignores the
trailing `~`, so no compile/reload), and the counter was read back through the
reflection bridge after an 8s wait.

- before = 0, after = 0 → observed callback count = **0**.
- Raw record: `results/watcher-callback-measurement.json`.

This confirms the earlier standalone probe with a fresh measurement of the tracker's
own callbacks: on this target the watcher delivers nothing, so only the scan is
load-bearing.

## Task 5.1 / 6.x — test suite

- Mock/helper suite: **607 tests OK** (`python -m unittest ...`, see `how-to-run.md`).
- Real-host suite: **41 tests OK (skipped=3)**.
  - `RefreshOnChangeRealHostTests`: 10/10 (watcher-error case removed; the pre-attach
    case retargeted to assert the scan directly; per-case reset reconciled to
    `OnCompilationCompleted` only).
  - `PlayModeCompileBlockRealHostTests`: 6/6.
  - `test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`
    (the `diagnose-exec-missing-after-auto-refresh` reload-loss regression) preserved
    and passing.
- The three skips are the pre-existing environment-gated cases (batch-mode lock,
  occupied-preferred-port sub-assertions), not product regressions.

## Task 5.2 — first-decision scan cost after the baseline walk was dropped

The install-time baseline walk was removed and the first decision was left to scan.
Diagnostic instrumentation (single `Stopwatch` around `ScanWatchedRoots`, removed
after measurement) showed:

- A single full walk (post-reload, on the main thread) costs **~150-300 ms**.
- Without an install-time warm, several post-reload requests (health probes, `/refresh`)
  each enumerate the tree on a request thread. The per-directory `Gate` serializes
  them, but the filesystem work does not, so their measured wall times inflate to
  **8.5-13.5 s**. That contention starved the Editor of log activity long enough for
  the CLI's stall watchdog to fire: `test_play_pause_play_resumes_against_real_host`
  failed deterministically twice with `unity_stalled` ("Unity log activity stalled for
  ~41 s").

Verdict: **the warmup path regressed** when the baseline walk was dropped.

The design (`design.md`, Decision 3) names "re-warming the cache without a watcher" as
the follow-up for exactly this case. It is implemented: `Install()` now calls
`WarmSnapshotCache`, which walks the watched roots once on the main thread after ready
and populates `DirSnapshots` **without producing a change signal** — the next decision
still scans and decides. `Install()` no longer runs a detection baseline walk.

Result after the warm:

- `PlayModeCompileBlockRealHostTests` 6/6 OK (506 s, vs 848 s when the contended scans
  were happening).
- Full real-host suite 41/41 OK (3 skipped).

No further follow-up is named for the warmup path; the re-warm closed it.

The only source change after the 41-test real-host run was a documentation comment on
`Install()` (no runtime logic); the run therefore covers the shipped behavior.

## Task 4.2 — no watcher as a mechanism in product surfaces

`grep -rni "watcher"` over `packages/`, `cli/`, `host/`, `tools/`, `README*.md`, and
`openspec/specs/` finds no watcher-backed description of the signal. The only remaining
mentions are the scan-only spec requirement ("with no dependency on a live filesystem
watcher") and test comments.
