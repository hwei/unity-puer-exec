## 1. Run the real-host suite

- [x] 1.1 Prerequisites confirmed with observed values before any claim: `UNITY_PROJECT_PATH` = `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project` (process env, overrides `.env`); `prepare_validation_host.py --dry-run` → `status: unchanged`, `embedded_package_shadowing: false`, `testables: ["com.txcombo.unity-puer-exec"]`; Editor `E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe`; preflight compile `status: passed`, `exit_code: 0`. No prerequisite was missing, so the run executed rather than skipped. Full table in `real-host-run.md`.
- [x] 1.2 Real-host suite run: **42 tests, OK (skipped=3), 2126.888s**. All six `PlayModeCompileBlockRealHostTests` cases ran and passed. Full per-case table in `real-host-run.md`.
- [x] 1.3 `test_play_settles_a_pending_change_then_reaches_playing` — the case that originally produced `[WinError 10054]` — **ran and passed**, reaching `playing` with exit code 0. No `status: "failed"` / exit 1 payload was observed on the play path.

## 2. Confirm the broadened catch does not mask a live condition

- [x] 2.1 No unattributed `not_available` was observed. Every boundary record in the run resolved to a specific attributed cause: `cold_launch_retry` → `attempt_count: 2`, `boundary_result: {"ok": true, "status": "stopped"}`; `preferred_port_rollover` → `preferred_port: 55231` held by `foreign_endpoint`, host rolled to `55232`, `mid_reload_rebind: "not_staged"`; `preferred_port_rollover_discovery` → `discovery_exit_code: 0`. The broadened `OSError` catch masked nothing live in this run. This is a negative observation over one run, not a proof.
- [x] 2.2 **No real transport reset occurred during the 35-minute run.** The live payload shape (`not_available` / exit 12 / errno in `error` / `transport_detail.reason`) was therefore *not* observed on a live endpoint; it remains verified only against the constructed `RemoteDisconnected` in `tests/test_direct_exec_client.py`. Recorded plainly rather than claimed as confirmation.

## 3. Closeout

- [x] 3.1 `meta.yaml` set to `evidence: host-validation, tests`. Both are honest here and the pairing is deliberate: a real host *was* exercised (so `host-validation` is genuinely obtained), but the reset classification itself rests on mocked tests (so `tests` is retained). The run was not a silent skip — all prerequisites were confirmed present first.
- [x] 3.2 `openspec validate validate-peer-reset-recovery-against-real-host --strict` → valid. `openspec validate --all` → see below.
- [x] 3.3 Closeout review below.

## Apply closeout review

### Which of the two confirmations was achieved

Design Decision 1 required this change to state plainly which kind of confirmation it reached.
It reached the weaker one:

- **Achieved: no regression observed on the play path against a live Editor.** The
  originating case `test_play_settles_a_pending_change_then_reaches_playing` passes, along with
  all five sibling play-mode cases, on Unity 2022.3.62f2 against the prepared host.
- **Not achieved: the reset path is confirmed on a live endpoint.** No peer reset occurred in
  the run. The classification remains verified against a constructed `RemoteDisconnected`
  only. A live run that reproduces no reset is not evidence about that path — the original
  failure was a single occurrence, which is exactly why it was hard to diagnose the first time.

The two must not be quoted interchangeably. `real-host-run.md` carries the full claim-by-claim
table so this distinction survives past the session that produced it.

### What is now ruled out

One risk was retired, and it was the risk the archived change itself flagged as its trade-off.
Design "Risks / Trade-offs" said catching `OSError` broadly "can swallow local errors". Over a
35-minute live run with three host-relaunch boundaries, two control-port rollovers, and several
domain reloads, **nothing surfaced as an unattributed `not_available`**. Every `not_available`
in the run resolved to a named, attributable cause. That negative result is weak on its own, but
it is not nothing, and it is the only evidence class a mocked test cannot produce.

### New follow-up candidates identified

**None.** No new candidate was found during this run. The candidates already carried forward
are unchanged: `classify-peer-reset-on-all-transport-callers` (audit + command-layer coverage,
unblocked).

### Disposition question for the human — do NOT auto-archive

This change's scope was "validate the fix against a real host", and it did that. But the change
*name* and its `evidence: host-validation` invite a stronger reading than the evidence supports:
a reader could reasonably infer the reset path is now confirmed live. It is not.

Three options, in the order I would rank them:

1. **Archive with the evidence-strength caveat carried in the artifact.** `real-host-run.md`
   states the distinction at the top level and in a claim-by-claim table, and `meta.yaml` keeps
   `tests` alongside `host-validation` so the archive record does not read as live-confirmed.
   The reset path stays honestly open; this change did its job.
2. **Keep the change open** pending repeated runs until a reset is observed. Honest, but it may
   be a long wait for a rare race, and it blocks nothing else. Not recommended as a gate.
3. **Fold the observation gap into `classify-peer-reset-on-all-transport-callers`** and archive
   this one now. Reasonable, since that change already owns the "what does each command do with a
   reset" question — but it would mix a live-validation question into a unit-coverage change.

Recommendation: **option 1**. It closes the work that was actually done, keeps the gap visible,
and does not silently convert "no regression observed" into "confirmed".

**Actions taken:** evidence recorded, tasks marked, nothing archived. Awaiting the human's
disposition before any `git commit` / `openspec archive` sequence.