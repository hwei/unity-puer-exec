# Proposal

## Why

`_read_compile_error_total` (in `cli/python/unity_puer_exec_runtime.py`) returns `0` whenever
it cannot read a usable `get-compile-errors` response. `stop` treats that value as the real
count, so a failed read — including a peer reset now classified as `not_available` by
`recover-peer-reset-transport-drop` — is reported to the agent as
`compile.compile_errors_total: 0`. That asserts "the deferred compile produced no errors" for a
read that never succeeded, which is a false statement in agent-facing output and contradicts the
`play-mode-control` promise that a compile failure is reported as a non-zero total.

Found and pinned during `2026-10-13-classify-peer-reset-on-all-transport-callers`
(`design.md` apply-closeout, follow-up #2). Direction chosen by the maintainer: **omit the field
rather than lie with `0`**.

## What Changes

- `_read_compile_error_total` distinguishes "read a total" from "could not read". It returns
  no total (not `0`) when the response is missing or unparseable.
- When the read fails, `stop`'s `compile` block **omits** `compile_errors_total` and includes an
  explicit `compile_error_total_available: false` marker. The numeric field only appears when its
  value is trustworthy.
- When the read succeeds, `stop`'s output is unchanged: `compile_errors_total` is present.
- `compile.outcome: "no_compile_observed"` keeps reporting `compile_errors_total: 0` — that is a
  positive observation, not a failed read.
- `get-compile-errors` / `get-compile-warnings` behavior is untouched; this is about what `stop`
  does with a failed enrichment read.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `play-mode-control`: the "Stop reports the deferred compile outcome" requirement currently
  promises a non-zero `compile_errors_total` for a compile failure without saying what `stop`
  reports when the total cannot be read. This change specifies the unreadable case: omit the
  field and flag it, rather than defaulting to `0`.

## Impact

- Affected code: `cli/python/unity_puer_exec_runtime.py` (`_read_compile_error_total`,
  `_stop_success_result`).
- Affected specs: `openspec/specs/play-mode-control/spec.md`.
- Affected validation: command-layer `stop` coverage plus the existing peer-reset suite.
- Inherited context: follow-up candidate from
  `openspec/changes/archive/2026-10-13-classify-peer-reset-on-all-transport-callers/design.md`.
