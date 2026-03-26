## Context

This change follows `add-exec-script-args`, which completed implementation but exposed a separate real-host regression problem during archive-readiness validation. The new finding is not that Unity always stalls; it is that sequential real-host cases can transition through a narrow teardown window where `ensure-stopped` has not fully drained, `Temp/UnityLockfile` is still fresh, and the next `wait-until-ready` call chooses recovery over a clean launch.

Two upstream findings remain true:

- The validation host is still an external verification target, not product source of truth.
- The real-host suite is still the repository-owned proof for project-scoped CLI behavior that mocked tests cannot replace.

The gap this design addresses is narrower: the repository does not currently guarantee a clean boundary between one real-host test case ending and the next one beginning, and the suite still carries at least two stale assertions from older CLI behavior (`--include-log-offset` and the promise-return error string).

This belongs in a change-local design because the exact fix is still open. The durable requirement is only that the repository-owned validation path be repeatable and aligned with the current CLI surface; the detailed stop/recovery tactics remain implementation choices.

## Goals / Non-Goals

**Goals:**

- Make the real-host regression path repeatable across sequential test cases in one suite run.
- Separate harness-sequencing failures from genuine product readiness regressions.
- Align real-host assertions and documentation with the current observation checkpoint surface (`log_range.start`) and current exec failure payloads.
- Preserve enough diagnostics to explain whether a failure came from incomplete stop, stale recovery state, or actual Unity/editor blockage.

**Non-Goals:**

- Redesign the full readiness model for all CLI commands.
- Change durable product requirements in `formal-cli-contract` unless the investigation proves the runtime contract itself is wrong.
- Treat every transient Unity idle period as a product defect.

## Decisions

### Decision: Treat this primarily as a validation-harness change, not a product-contract change

The first reliable evidence is sequence-dependent: individual real-host tests can pass in isolation while the full suite fails after earlier teardown. That points to harness isolation first.

Alternative considered: define the problem immediately as a CLI runtime bug. Rejected because the observed failures are mixed: some are stale assertions, some are teardown/recovery sequencing, and only the remainder may require runtime hardening.

### Decision: Update durable validation-host requirements, not formal CLI requirements

The durable truth here is that repository-owned real-host validation must remain repeatable and current. The detailed recovery heuristics, lockfile windows, and fixture implementation details belong in tests/runtime code, not in product-facing CLI spec text.

Alternative considered: modify `formal-cli-contract` now. Rejected because the current evidence does not yet show a stable user-facing contract change.

### Decision: Investigate stop/recovery handoff explicitly

The most actionable repro chain is:

1. `ensure-stopped --timeout-seconds 5` returns `not_stopped`
2. Unity exits shortly afterward
3. `UnityLockfile` remains fresh inside the recovery window
4. the next `wait-until-ready` enters `project_recovery`
5. no live Unity PID remains, so recovery idles into `unity_stalled`

The implementation should therefore inspect both fixture behavior and runtime branching around:

- `ensure-stopped` completion semantics
- `session_artifact` reuse
- fresh-lock recovery decisions when no Unity PID remains
- diagnostics preservation across the final stall payload

Alternative considered: only raise timeouts. Rejected because a longer timeout would hide the wrong branch rather than fixing or explaining it.

### Decision: Fold stale real-host assertions into the same change

The suite is currently not a trustworthy gate because it mixes harness instability with outdated expectations. Refreshing those expectations is part of restoring the suite as validation evidence.

Alternative considered: split stale assertions into a separate follow-up. Rejected because that would preserve a known-bad gate while investigating the readiness problem.

## Risks / Trade-offs

- [Harness fix masks a product bug] -> Keep at least one focused reproducer for the stop/recovery handoff and rerun the full real-host suite after the harness changes.
- [Runtime hardening broadens behavior beyond the real-host need] -> Prefer the smallest branch change that distinguishes "fresh lock but no recoverable editor" from genuine recovery.
- [Specs become too implementation-specific] -> Limit durable spec edits to repeatability and current validation workflow shape; keep lockfile/session-artifact details in code and change-local notes.
- [Unity shutdown timing remains machine-sensitive] -> Preserve diagnostics that include stop result, PID snapshot, and lock age so residual flakes stay attributable.

## Migration Plan

1. Update the validation-host OpenSpec truth so the suite targets the current observation checkpoint surface and requires a repeatable sequential boundary.
2. Reproduce the teardown-to-recovery stall with focused commands/tests and capture the minimum diagnostics needed for a durable regression.
3. Adjust the real-host harness and, if necessary, the runtime handoff between stop and readiness recovery.
4. Rerun targeted real-host cases, then the full `tests.test_real_host_integration` suite.
5. Return to `add-exec-script-args` archive only after this suite is trustworthy again.

## Open Questions

- Can the instability be fully removed by test-boundary hardening alone, or does `ensure_session_ready()` need a runtime branch change when recovery is chosen from a fresh lock without a live Unity process?
- Should `ensure-stopped` clear or invalidate stale session artifacts as part of project-scoped stop semantics, or is that too strong for the general runtime contract?
- Which diagnostics need to survive the final `unity_stalled` payload so contributors can distinguish "no process to recover" from "live editor blocked" without reading `Editor.log` manually?
