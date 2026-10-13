## Context

Seven `invoke_command` call sites in `cli/python/unity_puer_exec_runtime.py` are enumerated in
the proposal. The archived investigation verified only two of them. The question here is
narrow: after `recover-peer-reset-transport-drop` classifies a reset at the boundary, does
every command actually behave correctly, or do some call sites need their own treatment?

## Goals / Non-Goals

**Goals:**

- Establish, per command path, what a reset should produce.
- Turn "no call site wraps its own handler" into a recorded, verified statement rather than an
  assumption carried from the `play` investigation.

**Non-Goals:**

- Re-deriving the exception hierarchy or the envelope shape; the archived change owns that.
- Changing classification behavior. This change audits and tests.

## Decisions

### Decision 1: Audit before writing coverage

The table in the proposal records that no call site wraps the call in a handler, but does not
establish that the resulting behavior is correct for each command. `exec` and `wait-for-exec`
have their own recovery contracts, and a `not_available` body may or may not be the right
outcome for them. Write the per-command expectation first, then assert it.

### Decision 2: Separate the two claims

"The boundary classifies a reset as retryable" and "each command recovers from a reset" are
different claims with different dependencies. Coverage should distinguish them so a later
failure points at the right layer, and so this change remains meaningful even if applied before
the boundary fix.

### Decision 3: Report scope honestly

If the audit finds a call site whose correct contract genuinely differs from the others — for
example a call site that must stay terminal on a reset — record that as a finding rather than
widening the boundary to accommodate it. A genuine per-command difference is a spec question.

## Risks / Trade-offs

**Risk of duplicating the boundary fix's coverage** → mitigate by scoping this change's tests
to the *command* layer, asserting the outcome each command produces rather than re-asserting
the exception-to-status mapping.