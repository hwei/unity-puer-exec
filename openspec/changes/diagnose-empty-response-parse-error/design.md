## Context

Observed intermittently on the validation host while running the real-host suite. A
project-scoped `exec` returned a failure whose `error` was the text of a Python
`json.loads` exception:

```
status: "failed", exit_code: 2
error: "Expecting value: line 1 column 1 (char 0)"
situation: "An unexpected execution failure occurred. Check the error field for details. ..."
```

That message is what `json.loads("")` raises, so the command decoded an empty body and
passed the interpreter's message through as the caller-facing error. The payload otherwise
looked like a normal `failed` envelope (`attempts`, `boundary_result`, `cli_version`), so
the empty body was treated as a terminal execution failure rather than a distinguishable
response condition.

The durable contract already says all formal command results are machine-readable JSON and
that expected non-success machine states are branchable. An empty response body is a real,
nameable condition; leaking a decode-exception string as `error` makes it indistinguishable
from a script failure and forces an agent to parse prose.

## Goals / Non-Goals

**Goals:**

- Name the condition and classify it at the shared decoding boundary.
- Emit a structured payload an agent can branch on, with a continuation hint.
- Keep the exit-code model intact.

**Non-Goals:**

- The automatic-refresh request-recovery defect (`diagnose-exec-missing-after-auto-refresh`).
- The recovery-readiness resolution defect (`diagnose-recovery-readiness-timeout`).
- Retrying automatically or hiding the fact that a response was empty.

## Investigation record

### Site map (task 1.1)

The decode failure does not originate in `unity_puer_exec.run_cli` or in the runtime
`failed` envelope construction. Every command that posts to the Unity control service
funnels through one client, and that client owns the only HTTP body decode.

| # | Site | What it does | Role in the defect |
|---|---|---|---|
| 1 | `direct_exec_client.HttpTransport.post_json` | `json.loads(response.read().decode("utf-8"))` on the HTTP response body | **The raise site.** An empty body makes `json.loads("")` raise `JSONDecodeError("Expecting value", "", 0)`, whose `str()` is exactly `Expecting value: line 1 column 1 (char 0)`. |
| 2 | `direct_exec_client.invoke_command` | Posts the request, maps the body to an exit code, emits stdout/stderr | **The classifier.** Its `except ValueError` (added in `3af69aa`) catches the decode error and returns `status: "not_available"` with `error: "invalid response: <raw decode message>"`. |
| 3 | `unity_puer_exec_runtime.run_command` | Dispatches command handlers | Before `3af69aa`, the `ValueError` escaped site 2 and was caught here by `except ValueError` (runtime line 540), becoming `usage_error(...)` -> exit 2, `status: "failed"`, decode text on stderr. That is the observed `exit 2, status "failed"` shape. |
| 4 | `_invoke_exec` / `_run_wait_for_exec_impl` / `_run_get_compile_messages` / `_post_play_mode` / `_play_pre_settle` / `_read_compile_error_total` / `_invoke_reset_jsenv` | Command handlers | All call site 2; none decodes a body itself. The fix belongs at site 2, not per handler. |

### Source of the empty body (task 1.2)

The body was empty because the control endpoint accepted the request and then dropped
mid-domain-reload without writing a response, not because a subprocess produced no output
(the CLI is an in-process HTTP client here). Evidence:

- Commit `3af69aa` added site 2's `except ValueError` specifically because "mid-reload refresh polling exposed the latent bug".
- `_post_refresh_ready_timeout_seconds` and `_play_pre_settle` already document that "the endpoint can be down for the reload that ends the compile" and poll through it.
- The observed run was an `exec` warm-up that triggered the automatic refresh and compile cycle; the empty body arrived inside that window.

The classification records only what is observed -- an empty/unparseable response body --
and does not claim to know why the endpoint dropped. If a transport cause needs its own
change, this payload carries enough context to start it.

### Reproduction (task 1.3)

`.tmp/diag-empty-response-probe.py` drives the real boundary (`invoke_command`) with a
transport raising `JSONDecodeError("Expecting value", "", 0)`, sweeps every command
family, and asserts on the caller-facing payload. On current code it fails for all of
them: the decode message leaks into `error`, the status collapses into `not_available`,
and there is no `next_steps`. It also drives one `run_cli` `exec --base-url` invocation
end to end.

### Commands sharing the boundary (task 1.4)

Every command that posts to the control service shares site 2: `exec`, `wait-for-exec`,
`refresh`, `reset-jsenv`, `play-mode` (`play`/`pause`/`stop`), `get-compile-errors`,
`get-compile-warnings`, `get-log-source`, `get-log-briefs`, `get-blocker-state`, and
`resolve-blocker`. Commands that never post a body (`--version`, help, argument parsing)
do not. The reproduce probe sweeps these families.

## Decisions

### Decision 1: Classify at the boundary, not per command

Every formal command that decodes a response body shares the failure mode. If the empty
body is caught per command, the next command added repeats the bug. Task 1.4 confirms the
boundary is shared and task 2.1 fixes it there. The reproduction (1.3) asserts on the
caller-facing `error`, so the fix is judged by what the caller sees.

### Decision 2: The source of the empty body is investigated, not assumed

Three sources produce an empty body and only one of them is a transport problem: the
bridge returned no payload, the connection closed before the body, or the CLI's own
subprocess produced nothing. The structured state must describe the observed condition
accurately (empty/unparseable response), while 1.2 records which source actually occurred
so a follow-up can address a transport cause if that is what it was. The classification
does not pretend to know the cause.

### Decision 3: A distinct state, not a reclassified failure

The new condition must be distinguishable from a script `failed` and from other
process-level failures (task 2.4). It gets its own named status -- `empty_response` -- and
it does not reuse `failed` with a nicer message. The exit-code model is left intact: the
payload reuses `EXIT_NOT_AVAILABLE` (12) and names that code in an explicit
`exit_code_meaning` field, so the "no exit-code assignment changes" constraint from the
proposal holds while the status remains branchable. The raw interpreter text is moved out
of `error` into a `response_detail.decode_error` field so a caller never sees
`Expecting value: line 1 column 1 (char 0)` as the answer to "what happened".

## Validation notes

The fix is verified by the deterministic reproduction (`.tmp/diag-empty-response-probe.py`,
which now reports every family as structured and leak-free) and by the unit suites
(`tests.test_direct_exec_client`, `tests.test_unity_session_cli`, `tests.test_unity_puer_session`,
`tests.test_cli_version`, plus the full 606-test default suite). The real-host case that
originally surfaced the condition (`test_exec_rejects_legacy_fragment_script_against_real_host`)
was re-run and passed, but the empty body did **not** reproduce on that run: it is an
intermittent mid-reload race. That run therefore shows no host regression; it is not host
proof of the fix. The proof is the reproduction and the unit tests.

## Risks / Trade-offs

**[The empty body was masking a genuine server-side error]** → If the body was empty
because the server errored before writing a response, the structured state should carry
enough context (operation, endpoint, exit code) for the next investigation. The fix
reports the condition faithfully; it does not claim the server succeeded or failed.

**[Adding a status expands the caller-visible surface]** → A new named non-success state
is a contract addition. The provisional delta records it as an explicit scenario; if
investigation shows the condition is better folded into an existing state, the delta is
revised before tasks are finalized.
