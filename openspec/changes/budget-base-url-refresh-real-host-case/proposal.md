# Proposal

## Why

The real-host base-url automatic-refresh case is not green, and it is not green for a
reason the case itself encodes. `test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`
writes a compile-triggering source file and then runs `exec --base-url --wait-timeout-ms 1000`.
The write makes the server take its automatic-refresh branch, whose compile cycle settles
on a compile-scale budget; the 1000 ms request-wait budget expires first, so the exec
returns a non-terminal `running` response. The case then falls back to
`wait-for-exec --base-url`, and that command does not re-emit the refresh decision, so the
final payload has no `refresh` block and the case fails at `assertIn("refresh", ...)`.

This is a pre-existing deterministic failure, not a product regression: it reproduces
identically with the compile preflight disabled. It was surfaced while validating
`preflight-compile-check-before-editor-launch` and left as a `validation-gap` follow-up.

## What Changes

- Give the refresh-triggering first `exec` in the base-url case the same compile-scale
  settle budget the sibling refresh classes already use (`REFRESH_WAIT_TIMEOUT_MS`), so the
  CLI's settle-and-resubmit loop reaches the terminal exec response that carries the
  refresh decision.
- State the intent in the case: the terminal exec response, not a `wait-for-exec` fallback,
  is what carries `refresh.triggered` / `compile_triggering_change`.
- Keep the existing `wait-for-compile` second half of the case unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: adds a requirement that a real-host automatic-refresh case
  budget its refresh-triggering request at the compile scale, so the case asserts the
  refresh disclosure on the terminal response the refresh path actually produces.

## Impact

- `tests/test_real_host_integration.py`:
  `RealHostIntegrationTests.test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`
  (currently uses `WAIT_TIMEOUT_MS = 1000`; the refresh-scale constant exists only in the
  sibling classes).
- No product behavior change: the CLI's settle budget, the server's refresh decision, and
  the accepted-job lifecycle are unchanged.
- Related, deliberately not duplicated: `make-base-url-exec-refresh-recoverable` owns the
  deeper base-url continuation gap (an unsettled refresh handing the caller a request whose
  record exists nowhere). `document-exec-refresh-settle-budget` owns the help-surface
  statement. This change only makes the regression case budget correctly and assert what it
  claims to assert.
