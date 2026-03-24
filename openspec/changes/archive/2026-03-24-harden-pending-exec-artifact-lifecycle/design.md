## Context

Pending exec artifacts currently exist to bridge one specific gap: project-scoped `exec` can now enter an accepted `running` lifecycle before Unity is ready, and `wait-for-exec` can later submit the original request once startup completes.

The current shape is intentionally minimal:

- artifacts are stored under the target Unity project's `Temp/UnityPuerExec/pending_exec/`
- they are keyed by `request_id`
- they persist the original script content long enough for later recovery

This is good enough for the first Prompt A slice, but not yet a fully hardened lifecycle policy.

## Confirmed Current Behavior

The current implementation is intentionally narrow and only persists enough state to replay an accepted request later:

- `cli/python/unity_session_logs.py` stores each pending record as `Temp/UnityPuerExec/pending_exec/<request_id>.json` under the target Unity project.
- `cli/python/unity_puer_exec_runtime.py` writes the artifact when project-scoped `exec` cannot finish immediate startup readiness, and also before `--refresh-before-exec` begins its internal refresh phase.
- The persisted payload currently contains only the original `request_id`, the original script `code`, a boolean `refresh_before_exec`, and optional transient phase bookkeeping (`phase`, `refresh_request_id`).
- `wait-for-exec` reuses that payload to continue refresh work, retry compile-phase work, or replay the original exec once the project is ready again.
- The artifact is deleted only on explicit known terminal paths inside the CLI flow, mainly after a successful replay or after a non-recoverable refresh failure.
- Existing CLI tests cover creation, phase transitions (`refreshing`, `compiling`, `executing`), successful cleanup on completion, and continued reuse while the request remains recoverable.

## Confirmed Gaps

The current lifecycle remains intentionally loose:

- There is no explicit retention window or creation timestamp, so the implementation cannot distinguish an old leftover artifact from a still-recoverable request.
- There is no directory-level sweep or opportunistic cleanup for abandoned files left behind by interrupted CLI runs, crashes, or host restarts.
- Invalid or partially written JSON is treated the same as a missing record by the low-level reader, so the caller gets no distinction between corruption, expiry, and never-seen state.
- Cleanup semantics are incomplete for outcomes outside the happy path because removal happens only on a few explicit branches rather than through one centralized lifecycle policy.
- The stored payload keeps full script source without any documented upper bound or retention guarantee.
- The current public contract still effectively relies on the older `missing` concept from timeout-recovery work, which is too coarse once expiry and stale-artifact behavior become intentional.

## Decision

This problem should not be implemented opportunistically inside the spike itself.

The remaining work is small in code volume but not small in contract surface. Adding cleanup without first defining retention, stale-record semantics, and caller-visible outcomes would create hidden behavior changes in request recovery. The correct next step is a focused implementation-oriented follow-up change that formalizes the lifecycle first and then updates the CLI behavior and tests to match.

## Proposed Lifecycle Contract For The Follow-Up

The follow-up implementation should adopt an explicit pending exec artifact contract:

- Each artifact should carry enough metadata to reason about age and provenance, at minimum `created_at`, `updated_at`, `request_id`, lifecycle `phase`, and whether it represents an internal refresh sub-step.
- Pending artifacts should be retained only for a bounded recovery window. Once the retention window expires, the CLI should treat the record as stale rather than silently attempting replay.
- Successful terminal completion of the user request should always delete the artifact immediately.
- Non-recoverable terminal failures for the same request should also delete the artifact immediately once the CLI has enough confidence that replay is no longer correct.
- Recoverable `running` and compile/recovery states should keep the artifact and refresh its metadata so later waits can still continue the same request.
- Project-scoped `exec` and `wait-for-exec` should perform opportunistic cleanup of obviously stale pending artifact files for the same project before or after operating on the target record.
- Malformed artifact files should be removed opportunistically and treated as stale local leftovers, not as valid recoverable requests.
- The caller-facing behavior should continue to prefer a simple machine-readable status, but the implementation change should decide whether expired/corrupt leftovers remain folded into `missing` or surface a more explicit stale-local-artifact status.

## Follow-On Implementation Tasks

The implementation-oriented follow-up should cover at least:

1. Extend the pending artifact schema and repository helpers to persist timestamps and lifecycle metadata.
2. Centralize pending artifact retention and cleanup decisions instead of scattering delete behavior across individual exec branches.
3. Add stale-record detection and opportunistic cleanup for expired or malformed pending artifact files.
4. Decide and document the caller-visible result for expired or corrupted pending records, including whether it stays `missing` or becomes a distinct status.
5. Add focused unit tests for expiry, stale cleanup, malformed artifact handling, and immediate deletion on terminal outcomes.
6. Add at least one host-validation pass that proves the new lifecycle still preserves the accepted `exec -> running -> wait-for-exec` recovery path.

## Open Questions

- What retention window is short enough to avoid Temp-directory buildup but long enough to preserve realistic agent recovery flows?
- Should expiry continue to collapse into `missing`, or should the CLI expose a more explicit stale-local-artifact status once the lifecycle is formalized?
- Should opportunistic cleanup scan only the addressed request plus clearly expired siblings, or sweep the full pending directory each time?
- Is script-body persistence acceptable for the whole retention window, or should the future implementation move toward a smaller replay token model?

## Intended Outcome

This follow-up should eventually expand into a complete change that:

- defines the pending exec artifact lifecycle explicitly
- adds the necessary cleanup and retention behavior
- proves the behavior with focused tests

Until then, this spike exists only to keep the hygiene concern visible and bounded.
