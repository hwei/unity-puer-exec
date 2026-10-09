## Context

Continues `2026-09-21-diagnose-exec-missing-after-auto-refresh`. That change fixed the
deterministic cause (the settle budget was `--wait-timeout-ms`, so a 1.0 s window could never
cover a compile+reload) and explicitly left the `missing` classification and the branch
structure intact: "the fix does not simply silence `missing` for all requests". Its closeout
recorded this change as the `product-improvement` candidate that remained.

Verified state on current code. A base-url `exec` whose settle never returns ready emits:

```
exit 10, status "running", phase "refreshing", request_id R
next_steps: [{command: "wait-for-exec",
              when: "you want to continue waiting for the accepted request to finish"}]
```

and `wait-for-exec --base-url --request-id R` then answers exit 13 / `missing`
(`no recoverable record exists for request_id`). The response advertises an *accepted*
request that the server never accepted: `HandleExecAsync` returns the refreshing phase before
`TryAcceptExecRequest`, and base-url mode keeps no client-side record.

## Goals / Non-Goals

**Goals:**

- Make the documented continuation for a base-url request actually converge on the script
  result, or stop advertising a continuation that cannot.
- Keep `missing` meaning what it means: the addressed service has no recoverable record.
- Preserve the accepted-job lifecycle: no resubmit of a request that may already have run.

- Make the two budgets distinguishable from the help alone: the per-request wait a caller
  chooses, and the compile-scale budget the CLI settles a refresh on.

**Non-Goals:**

- Re-litigating the settle budget, the server's refresh decision, or the non-terminal refresh
  contract itself (settled by the previous change).
- Redesigning the pending-exec artifact lifecycle for project-path mode.
- The intermittent launch-recovery and CLI empty-response flakes, which have their own
  changes.
- A caller-facing settle-budget knob on `exec`. `wait-for-compile` has
  `--settle-timeout-seconds`; adding one to `exec` would let a caller make the very mistake the
  help statement documents. If the investigation finds a reason to want one, it is recorded as
  a follow-up candidate.

## Decisions

### Decision 1: The continuation is the gap, and there are two candidate designs

Two mutually exclusive approaches; task 1.2 must pick one with evidence.

- **Retry in-process**: the CLI already holds the code. Instead of returning a
  non-terminal response at `settled is None or refresh_attempts >= 1`, keep settling and
  resubmitting under the same `request_id` until the script runs or the compile-scale budget
  is exhausted. No new persistent surface; the cost is that `exec` can block for the settle
  budget when a refresh is genuinely stuck.
- **Carry a client-side record**: give base-url mode a replay record keyed by `request_id`
  (the project-path pending artifact is keyed on a project path, which base-url mode does not
  have), so `wait-for-exec --base-url` can replay the exec the way project-path mode does.
  This makes the advertised continuation literally true, at the cost of a new CLI-owned
  storage surface and a new lifecycle to bound and sweep.

### Decision 2: The exhausted-budget outcome must be a real terminal state

If the budget is genuinely exhausted, the CLI must not fall back to `missing` (that is the
defect) and must not silently drop a request whose script may have run. Task 1.3 must name
the outcome and the guidance it carries, and say which invariant makes a resubmit safe --
`diagnose-exec-missing-after-auto-refresh` established that the server has not accepted the
job at the refreshing phase, so a resubmit there runs the script for the first time.

### Decision 3: `missing` keeps its meaning

The fix must not treat `missing` as resubmittable in general. A genuinely absent or expired
record still reports `missing`; only the branches where the CLI itself left the request
unsettled change shape.

### Decision 4: Help states the budget's nature, not a literal number

Help SHALL say the settle runs on a compile-scale budget independent of `--wait-timeout-ms`,
without naming a number, so the prose cannot drift from
`unity_session.DEFAULT_READY_TIMEOUT_SECONDS`. The statement goes in the wait/timeout guidance
as well as the automatic-refresh line. It is written after Decision 1, so it describes the
continuation that actually ships (with in-process retry, `exec` may block for the settle budget,
and help must say so). `wait-for-compile --settle-timeout-seconds` describes the same cycle,
and the two surfaces must not contradict each other.

## Risks / Trade-offs

**[Blocking longer on a stuck refresh is a worse failure mode than returning early]** → If
Decision 1 lands on in-process retry, `exec` can hold for the full compile-scale budget on a
refresh that never settles. The mitigation is a bound plus an honest terminal outcome
(Decision 2), not a return to the unreachable-continuation shape.

**[A client-side base-url record is a new persistence surface]** → If Decision 1 lands on a
record, it needs a home, a key, a retention bound, and a sweep, and it must not become a
second source of truth that disagrees with the server. The project-path artifact's rules
(`PENDING_EXEC_RETENTION_MS`, schema version, malformed-file deletion) are the precedent to
follow or explicitly reject.

**[A new help line weakens an existing help assertion]** → Help-content tests assert on
strings; adding text must not remove or relax an existing guarantee. Each touched assertion is
reviewed deliberately rather than deleted when it fails.

**[The unit layer may not reproduce the real ordering]** → The clock-modelled settle harness
introduced by the previous change expresses the budget arithmetic deterministically. Whether
a real reload interleaves as modelled still has to be confirmed on the host (task 3.2).
