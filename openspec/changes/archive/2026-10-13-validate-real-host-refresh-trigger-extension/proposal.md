## Why

While writing the new real-host refresh case for
`2026-10-13-make-base-url-exec-refresh-recoverable`, the probe was authored as
`BaseUrlRefreshContinuationProbe` with no extension. The Editor's change signal only watches
compile-triggering code files, so the write staged as `no_pending_change` and the case failed
with "refresh did not trigger" — a symptom three steps removed from the cause, at the cost of a
full Editor launch per attempt.

`_write_compile_triggering_probe` in `tests/test_real_host_integration.py` accepts the caller's
file name unvalidated. Every current call site happens to pass an explicit `.cs` suffix, so the
helper never had to cope with the mistake; it simply had no way to catch it. The same confusion
also shapes the wait helper's failure message: `_wait_for_refresh_pending` reports the last
observed `refresh` block without saying which extensions are watched, so a reader cannot tell a
mistyped probe from a probe the Editor legitimately did not pick up.

## What Changes

- `_write_compile_triggering_probe` rejects a probe name outside the Editor's watched
  compile-triggering extension set before anything is written, naming the watched extensions.
  A mistyped probe then fails locally instead of after an Editor launch.
- The watched set is read from what the durable help already documents — C# sources, assembly
  definitions and references, and compiler response files — rather than introduced as a second
  list that could drift.
- `_wait_for_refresh_pending` names the watched extensions and the observed `skipped_reason` in
  its failure message, while keeping the existing distinct message for a control endpoint that
  never returned at all.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: adds a requirement that a real-host refresh trigger is staged
  with a watched compile-triggering extension, and that a change signal which never becomes
  pending fails with the watched extensions and the observed `skipped_reason` named, so a
  mistyped probe is distinguishable from a genuine detection failure.

## Impact

- Affected code: `tests/test_real_host_integration.py` (`_write_compile_triggering_probe`,
  `_wait_for_refresh_pending`).
- Affected behavior: real-host test staging only. No product code changes and no change to what
  the CLI emits.
- Affected validation: the real-host refresh cases. Every current call site already passes
  `.cs`, so the new validation is expected to break none of them — verified by running the
  suite, not asserted in the unit layer.
- Inherited findings: observed while applying `2026-10-13-make-base-url-exec-refresh-recoverable`;
  recorded in that change's closeout as a `validation-gap` candidate. The separate
  `product-improvement` candidate from the same closeout is tracked in
  `restore-base-url-exec-continuation-guidance`.