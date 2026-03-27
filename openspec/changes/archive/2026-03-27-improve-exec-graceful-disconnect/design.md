## Context

The validation record in `validate-openupm-real-host-usability` showed a benign-but-messy failure mode: import churn delayed the response long enough that the original wait path stopped caring, yet the same `request_id` later recovered successfully. The remaining problem is the noisy transport exception emitted while the server tries to write back to a connection the client no longer holds open.

## Goals / Non-Goals

**Goals:**
- Make accepted exec request shutdown and response delivery behave more gracefully when the first waiting client is gone.
- Keep the current `request_id` recovery model intact.

**Non-Goals:**
- Redesign exec identity or async observation.
- Hide genuine transport failures that do indicate lost work.

## Decisions

### Decision: Treat disconnect noise as a request-lifecycle concern, not as a script-runtime concern

The script may still be healthy, so the contract should separate transport close behavior from script failure semantics.

### Decision: Preserve recovery-first semantics

An accepted request that can still complete should remain recoverable through `wait-for-exec` or result-marker observation even if the first response path disconnects.

## Risks / Trade-offs

- [Risk] Over-suppressing errors could hide real transport defects. Mitigation: narrow the graceful path to known accepted-request disconnect cases and keep diagnostics available.
