## Why

The real-host suite assumes the control endpoint is stable between a request and the next
probe. Unity drops that endpoint around every domain reload: a script compile, a play-mode
exit with a deferred compile, and the assembly reload that ends it. A helper that probes
once and asserts therefore fails for a reason unrelated to the behavior under test.

This surfaced while landing `surface-play-mode-compile-block`:
`test_play_mode_skips_refresh_and_preserves_pending_change` failed on
`_health()` `assertIsNotNone` with `[WinError 10054]` immediately after play exit, then
needed a manually retried run to pass. `_wait_for_refresh_pending` polls through the same
`_health()` and has the same defect.

The tolerant pattern already exists in two helpers (`_wait_for_play_exit`,
`_wait_for_refresh_state` after the play-mode work) and is duplicated in two test classes.
The suite needs one shared, tolerant endpoint probe instead of per-class copies.

## What Changes

- Add one shared tolerant endpoint probe on `_SharedRealHostDevice`: it retries a
  transport failure within a bound, re-resolves the project's published control-port
  endpoint, and returns the endpoint and payload (or raises a named timeout).
- Route the single-shot `_health` probes and `_wait_for_refresh_pending` through it, so a
  probe landing in a domain reload waits the reload out instead of failing the case.
- Keep one-shot readiness assertions only where the case genuinely requires an endpoint
  that is up now, and make that requirement explicit in the assertion message.
- De-duplicate the copied play-mode/refresh helpers between `RefreshOnChangeRealHostTests`
  and `PlayModeCompileBlockRealHostTests` onto the shared device.
- Do not change any product code; this is test-harness robustness only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — the affected behavior is the test harness's own fault tolerance, not a
caller-facing requirement. If the investigation finds a durable validation rule, fold it
into `validation-host-integration` in this change.)

## Impact

- `tests/test_real_host_integration.py`: the shared device's probe helpers, the
  per-class duplicates, and every case that currently calls the one-shot `_health`.
- No change to `cli/`, `packages/`, or the durable specs.
- Verification stays under the opt-in `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1` gate.
