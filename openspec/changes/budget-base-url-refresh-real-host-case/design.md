# Design

## Context

See proposal.md — Why. The relevant mechanics:

- `RealHostIntegrationTests.test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`
  is in `tests/test_real_host_integration.py` and uses the module-level `WAIT_TIMEOUT_MS = 1000`
  for its first, refresh-triggering `exec`.
- The sibling refresh classes (`RefreshOnChangeRealHostTests`,
  `PlayModeCompileBlockRealHostTests`) already define `REFRESH_WAIT_TIMEOUT_MS = 300_000` and use
  it for the same kind of request.
- The CLI's `exec` loop settles an automatic refresh on its own compile-scale budget and then
  re-submits; the terminal `exec` response carries the captured `refresh` block. The
  `wait-for-exec` command is a separate continuation and does not re-emit it.

## Goals / Non-Goals

**Goals:**
- Make the base-url case assert what it claims: the refresh decision on the terminal exec
  response.
- Keep the change to the validation layer; no product behavior change.

**Non-Goals:**
- Closing the base-url continuation gap (an unsettled refresh handing the caller a request
  whose record exists nowhere) — owned by `make-base-url-exec-refresh-recoverable`.
- Documenting the settle budget on help surfaces — owned by `document-exec-refresh-settle-budget`.

## Decisions

### D1. Budget the refresh-triggering exec at the compile scale

Give the first `exec` the same `REFRESH_WAIT_TIMEOUT_MS = 300_000` the sibling classes use,
promoted to the class (or module) so the intent is named rather than inlined.

Alternative considered: keep the 1000 ms budget and accept the non-terminal handoff. Rejected
because the case then never asserts the exec path's refresh disclosure; it asserts a
continuation from a different command, which is not the behavior under test.

Alternative considered: make base-url `wait-for-exec` carry the refresh decision. Rejected
here as scope overlap with `make-base-url-exec-refresh-recoverable`, which owns that contract
decision.

### D2. Assert the disclosure on the terminal exec response only

The case SHALL not treat a `wait-for-exec` payload as evidence that the refresh decision was
disclosed. If the exec still returns non-terminal, the case fails with that named — which is
the honest signal, since a genuinely unsettled refresh is the sibling change's problem.

## Risks / Trade-offs

- [A larger budget makes a genuine hang slower to fail] → Bounded by the same 300 s the sibling
  refresh classes already accept for a real compile cycle.
- [The refresh may still not settle within 300 s on a slow host] → The case fails loudly; that
  is a real-host condition worth surfacing, not something to paper over with a skip.

## Migration Plan

Not applicable — a single validation case changes; no product or data migration.

## Open Questions

None.
