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

## Audit: per-call-site expectation on a peer reset

Line numbers re-derived from the current `cli/python/unity_puer_exec_runtime.py` (they still
match the proposal table). "Boundary" below means `direct_exec_client.invoke_command`, which
after `recover-peer-reset-transport-drop` turns `RemoteDisconnected`/`OSError`/`HTTPException`
into a `not_available` body (exit 12) with the errno preserved in `error` and the exception
class in `transport_detail.reason`. No enclosing function wraps its own reset handler, so each
command inherits that body and only has to decide what its own contract is *on top of* it.

| Line | Enclosing function | Command path | Own retry? | Expected report on a reset |
|---|---|---|---|---|
| 1020 | `_invoke_exec` | `exec`; `wait-for-exec` replay | no | structured `not_available` / exit 12, errno + `transport_detail` intact; in project mode the pending request stays replayable |
| 1412 | `_invoke_reset_jsenv` | **none** | n/a | **finding:** dead code, no caller and no `reset-jsenv` command in the parser; there is no command-layer behavior to assert |
| 1800 | `_run_wait_for_exec_impl` | `wait-for-exec` | no | structured `not_available` / exit 12, errno intact; pending request stays replayable |
| 2325 | `_run_get_compile_messages` | `get-compile-errors` / `get-compile-warnings` | no | propagate `not_available` / exit 12 unchanged (the `exit_code != 0` branch returns before body normalization) |
| 2446 | `_post_play_mode` | `play` / `pause` / `stop` | yes (bounded) | retry the reload edge; terminal `not_available` / exit 12 with the errno. Covered by the archived change's spec |
| 2534 | `_play_pre_settle` | `play` / `pause` / `stop` | yes (loop) | settle/retry; terminal body surfaced as-is |
| 2656 | `_read_compile_error_total` | helper inside the `stop` success path | no | **finding:** best-effort enrichment; a reset body has no `total`, so it silently degrades to `0` rather than failing the `stop`. Acceptable for an enrichment read, but named so it is not mistaken for a classified result |

### Per-command decision

- `exec` / `wait-for-exec`: the reset is non-terminal for an *accepted* request. The command
  reports the structured body and, in project mode, keeps the pending artifact so a later
  `wait-for-exec --request-id` can replay it. This is the command's own recovery contract; it
  is **not** the same claim as the boundary classifying the exception.
- `get-compile-errors` / `get-compile-warnings`: a pure read with no replay record; the only
  correct behavior is to surface the classified body unchanged. No per-command contract beyond
  the shared boundary.
- `play` / `pause` / `stop`: the only call sites that retry, and they already do so. Covered.
- `_read_compile_error_total`: intentionally best-effort. Its degradation is recorded as a
  finding rather than "fixed", because widening it into a classified failure would change
  `stop`'s success shape for a value it only appends to its result.
- `_invoke_reset_jsenv`: dead code. Removing it is not in this change's scope (behavior-preserving
  validation change); recorded as a follow-up candidate.

No call site was found to need a contract genuinely different from the shared boundary in a way
that requires a spec delta. The two findings above are the honest residue.

## Apply closeout

- **Spec delta needed?** No. The audit found no per-command contract that diverges from the
  shared boundary. `exec`/`wait-for-exec` keep their existing replay contract, the compile-message
  reads surface the body unchanged, and the play-mode retry contract is already specified by
  `play-mode-control`. The change remains `skip_specs: true` as proposed.
- **New follow-up candidates identified** (surface for human discussion; not promoted here):
  - `product-improvement` / `tooling-improvement`: `_invoke_reset_jsenv`
    (`cli/python/unity_puer_exec_runtime.py:1411`) is dead code — no caller and no `reset-jsenv`
    command in the parser. Removing it would shrink the set of transport call sites back to the
    ones that actually serve a command.
  - `validation-gap` / `product-improvement`: `_read_compile_error_total` silently degrades a
    reset to `0`, so `stop` can report `compile_errors_total: 0` from a read that did not
    succeed. Pinned by `test_stop_survives_a_reset_while_reading_compile_error_total`; whether
    the field should be omitted or flagged on an unreadable total is a product decision.
  - `validation-gap`: this change's coverage is mocked at the `invoke_command` boundary, exactly
    like the archived `recover-peer-reset-transport-drop`. The archived
    `validate-peer-reset-recovery-against-real-host` already recorded that no live reset was ever
    observed, so the command-layer contract added here inherits that residual risk. It is not new
    to this change; flagged so the two mock-only layers are not mistaken for live confirmation.
- **Evidence:** default suite 655 tests OK; `openspec validate` strict + `--all` (36 passed, 0
  failed). `meta.yaml` evidence stays `tests`.

## Risks / Trade-offs

**Risk of duplicating the boundary fix's coverage** → mitigate by scoping this change's tests
to the *command* layer, asserting the outcome each command produces rather than re-asserting
the exception-to-status mapping.