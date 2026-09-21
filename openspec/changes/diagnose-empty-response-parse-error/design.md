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
process-level failures (task 2.4). It gets its own named status; it does not reuse
`failed` with a nicer message.

## Risks / Trade-offs

**[The empty body was masking a genuine server-side error]** → If the body was empty
because the server errored before writing a response, the structured state should carry
enough context (operation, endpoint, exit code) for the next investigation. The fix
reports the condition faithfully; it does not claim the server succeeded or failed.

**[Adding a status expands the caller-visible surface]** → A new named non-success state
is a contract addition. The provisional delta records it as an explicit scenario; if
investigation shows the condition is better folded into an existing state, the delta is
revised before tasks are finalized.
