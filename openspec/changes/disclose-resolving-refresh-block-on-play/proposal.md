# Proposal

## Why

`fix-unchanged-content-refresh-loop` added `paths_suppressed` to the refresh block so a decision that
dropped a candidate is distinguishable from one that saw nothing. On `exec` that disclosure reaches
the caller, because the terminal response carries the refresh block of the decision that resolved the
request. On `play` it does not.

`_play_pre_settle` retains a refresh block only inside its `_is_refresh_pending_response` branch —
`refresh_block = _extract_refresh_block(stdout_text) or refresh_block` — so it keeps the block from
the poll that *dispatched* and discards the block from the poll that *resolved*. The issue #3
reproduction shows the consequence: `play` reached `play_state: "playing"` in 14.0 s with
`refresh.triggered: true, paths_suppressed: [], elapsed_ms: 13`, which reads as "a refresh ran and
nothing was suppressed". What actually happened is that a later poll suppressed the same path and
returned `triggered: false` with that path in `paths_suppressed` — the only evidence that the fix
fired, and it is the one block thrown away.

An operator reading a `play` transcript therefore cannot tell a play that resolved because the new
suppression worked from a play that resolved because nothing was ever pending. The diagnostics
requirement the refresh block exists to satisfy is met for `exec` and not for `play`.

## What Changes

- The `play` pre-settle retains the refresh block from the decision that resolved the settle, not
  only from the ones that dispatched, so the success payload discloses the suppressing decision and
  its `paths_suppressed`.
- A play that dispatched a refresh and then resolved on a suppressed decision discloses both facts:
  that a refresh ran, and that the resolving decision suppressed the paths named.
- A play whose settle never dispatched a refresh keeps disclosing no refresh, exactly as today.
- No protocol change and no host change. The block the server already returns on the resolving
  `/refresh` response is the block that gets kept.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `play-mode-control`: "Play settles pending code before entering play mode" gains the property that
  the refresh disclosure in a play result is the resolving decision's, so a suppressed settle is
  distinguishable from a settle that saw nothing pending.

## Impact

- **CLI**: `cli/python/unity_puer_exec_runtime.py` — `_play_pre_settle`'s refresh-block retention,
  and the payload built by `_play_success_result`.
- **Host**: none.
- **Tests**: mocked coverage for which block survives a dispatch-then-suppress settle; a real-host
  case that a `play` after a content-identical rewrite names the probe in `paths_suppressed`.
- **Compatibility**: additive to the `play` payload. The existing `refresh` object keeps every field;
  only its values change for the dispatch-then-suppress case, which today reports an empty
  `paths_suppressed` that was never accurate.
- **Upstream**: inherits `fix-unchanged-content-refresh-loop`'s `paths_suppressed` disclosure and its
  finding that the resolving decision is the one worth reading. Deliberately does not revisit the
  exec-side retention rules or the refresh-block retention covered by
  `package-editmode-test-harness`, which is about play-mode suppression of an exec refresh and is
  unaffected.
