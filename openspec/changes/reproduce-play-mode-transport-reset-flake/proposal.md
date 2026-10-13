## Why

While validating `2026-10-13-validate-real-host-refresh-trigger-extension`, the real-host case
`test_play_settles_a_pending_change_then_reaches_playing` failed once with
`{"status":"failed","operation":"play","error":"[WinError 10054] ... forcibly closed"}` and passed
on immediate retry. `2026-10-12-recover-play-mode-transport-failures` made `_post_play_mode` retry
a dropped endpoint within its bound and preserve the formal boundary exit code, so this observation
suggests either the bound is too short for a real reload edge or the drop landed outside the branch
that retries.

This is a validation gap: the retry contract is asserted, but a residual transport reset on the
`play` path is neither reproduced deterministically nor explained.

## What Changes

- Reproduce the `WinError 10054` on the `play` path against the validation host under a controlled
  reload edge, or record that it is environmental and not reproducible within a bounded run.
- Establish whether the existing retry bound covers the observed edge.
- If it does not, record the concrete gap and recommend a separate product change rather than
  absorbing the fix here.
- No product code change in this change unless the investigation cannot proceed without one.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No planned spec-level change: the outcome is an investigation finding, and any behavior change it
justifies would be proposed separately. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected code: `tests/test_real_host_integration.py` only if a deterministic reproduction can be
  added.
- Affected behavior: none unless the investigation identifies a fix; that fix is out of scope here.
- Affected validation: real-host, reusing the existing play-mode and reload helpers.
- Inherited finding: recorded as the `validation-gap` follow-up in the closeout of
  `2026-10-13-validate-real-host-refresh-trigger-extension`.
