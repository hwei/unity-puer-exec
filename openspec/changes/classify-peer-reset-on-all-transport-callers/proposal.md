## Why

The archived investigation `2026-10-13-reproduce-play-mode-transport-reset-flake` established
that a peer reset escapes `direct_exec_client.invoke_command` and surfaces as
`status: "failed"` / exit `1`. That investigation audited two call paths only:
`_post_play_mode` (exposed) and `unity_session_wait.probe_health` (safe, because it wraps the
probe in a blanket `except Exception` that degrades to `(None, str(exc))`).

It did not audit the other call sites. An AST scan of
`cli/python/unity_puer_exec_runtime.py` lists seven `invoke_command` call sites:

| Line | Enclosing function | Own retry / handler? |
|---|---|---|
| 1020 | `_invoke_exec` | — |
| 1412 | `_invoke_reset_jsenv` | — |
| 1800 | `_run_wait_for_exec_impl` | — |
| 2325 | `_run_get_compile_messages` | — |
| 2446 | `_post_play_mode` | retries (but unreachable for a reset) |
| 2534 | `_play_pre_settle` | retries (but unreachable for a reset) |
| 2656 | `_read_compile_error_total` | — |

None of the call sites wraps the call in its own exception handler, so the escape reaches the
top-level `except Exception` for every command above, not only `play`. A reset during `exec` or
`wait-for-exec` would present as the same opaque `status: "failed"`.

This is a coverage question, not a second fix. `recover-peer-reset-transport-drop` fixes the
shared boundary and would make every one of these call sites receive a structured body; this
change exists to confirm that end-to-end rather than assume it.

## What Changes

- Audit each of the seven `invoke_command` call sites for how it should classify a reset, and
  record the answer.
- Add coverage that asserts a reset produces a structured, correctly-classified result on
  each command path — not only on `play`.
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
  differs.
- Affected validation: unit coverage per command path.
- `blocked_by`: none, but it should be read alongside `recover-peer-reset-transport-drop` —
  asserting "the boundary classifies a reset" is cheap and passes either way, while asserting
  "each command recovers from a reset" depends on that fix landing first.