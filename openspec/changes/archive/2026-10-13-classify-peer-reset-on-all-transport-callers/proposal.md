## Why

The original premise of this change is now **resolved**. `recover-peer-reset-transport-drop`
(archived `2026-10-13-recover-peer-reset-transport-drop`) widened the handlers in
`direct_exec_client.invoke_command` to catch `OSError` and `http.client.HTTPException`, so
`http.client.RemoteDisconnected` no longer escapes the boundary. All seven call sites listed
below now receive a structured `not_available` / exit-12 body with the reset errno preserved in
`error` and the exception class named in `transport_detail.reason`.

What survives is the **verification** half of this change, which was never wrong and is not
covered by that fix. Two things remain genuinely open:

1. Nobody has recorded what each of the seven call sites *should* report when the endpoint
   resets. The boundary fix makes a structured body available everywhere, but whether a given
   command should retry, treat the reset as terminal, or surface it directly is still an
   unwritten per-command contract.
2. Only `play` has command-layer assertions. `exec`, `reset-jsenv`, `wait-for-exec`,
   `get-compile-messages`, and `_read_compile_error_total` now receive a correctly classified
   body, but nothing asserts they classify it *correctly* for their own command semantics — as
   opposed to merely not crashing.

So this is no longer a fix and no longer a "does the boundary catch it" check. It is an audit
plus command-layer coverage, over behavior that is already implemented.

### Call sites to audit

An AST scan of `cli/python/unity_puer_exec_runtime.py` lists seven `invoke_command` call sites:

| Line | Enclosing function | Own retry / handler? |
|---|---|---|
| 1020 | `_invoke_exec` | — |
| 1412 | `_invoke_reset_jsenv` | — |
| 1800 | `_run_wait_for_exec_impl` | — |
| 2325 | `_run_get_compile_messages` | — |
| 2446 | `_post_play_mode` | retries; **covered** by the archived change |
| 2534 | `_play_pre_settle` | retries; **covered** by the archived change |
| 2656 | `_read_compile_error_total` | — |

Line numbers are as of the archived change and must be re-derived, not trusted.

## What Changes

- Audit each `invoke_command` call site and record what the owning command should report when
  the endpoint resets: retry within a bound, report as terminal, or surface directly.
- Add command-layer coverage asserting each command produces a correctly classified result for
  a reset — not only on `play`, and not a re-assertion of the boundary mapping.
- Confirm whether any call site needs its own treatment beyond the shared boundary fix, and
  if so say so explicitly rather than leaving it implied.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No planned spec-level change: this is a validation-coverage change over behavior that
`recover-peer-reset-transport-drop` already specifies. `.openspec.yaml` sets
`skip_specs: true`. If the audit finds a genuinely different per-command contract, that becomes
a spec delta proposed separately.

## Impact

- Affected code: `tests/` only, unless the audit finds a call site whose contract genuinely
  differs from the boundary's `not_available`.
- Affected validation: unit coverage per command path.
- `blocked_by`: `recover-peer-reset-transport-drop` is resolved, so this is unblocked. The
  audit should be read against the archived change rather than the original reproduction.