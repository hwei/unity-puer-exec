## Why

A formal command can surface a raw Python JSON parse error as its machine-readable
`error`, instead of a branchable state. Observed on the validation host during a real-host
run of `tests.test_real_host_integration` (case
`test_exec_rejects_legacy_fragment_script_against_real_host`):

```
_warm_up_project_exec -> exit 2, status "failed"
  error: "Expecting value: line 1 column 1 (char 0)"
  situation: "An unexpected execution failure occurred. Check the error field for details.
              Note: if the error is async_result_not_supported, the script body executed
              but returned a Promise - use exec --help-status to see the warning status."
  attempts: [{attempt: 1, exit_code: 2, status: "failed",
              error: "Expecting value: line 1 column 1 (char 0)"}]
```

`Expecting value: line 1 column 1 (char 0)` is the message of a Python `json.loads` on an
empty string. The command's response body was empty (an empty `stdout`, no structured
payload), and the CLI's decoding surfaced the interpreter's exception text as the
caller-facing `error`. The caller is handed prose, not a state it can branch on.

This contradicts the durable contract "Formal command results are machine-readable JSON":
an unexpected process-level condition still has to arrive as structured JSON, and an agent
must be able to distinguish "the bridge returned an empty body" from other failures. The
same `error` string also violates "Exit codes remain part of the formal machine contract"
in spirit — the caller cannot tell what the exit code 2 means from the payload.

The condition was intermittent, so the investigation has to establish the source of the
empty body (server sent nothing mid-reload, transport closed early, or a subprocess
emitted nothing) before the fix is chosen.

## What Changes

- Reproduce the empty-body condition and identify its source: the server's response, the
  transport, or the CLI's own subprocess invocation.
- Replace the raw decode failure with a structured, branchable machine state (a named
  status such as an empty/unparseable-response condition) that carries the operation, the
  exit code meaning, and a `next_steps` continuation — never the interpreter's message as
  the `error`.
- Apply this at the shared decoding boundary so every command family benefits, not only
  `exec`.
- The durable contract delta below is **provisional**: it names the observed case as an
  explicit scenario without changing the requirement's normative text.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds one explicit scenario to "Formal command results are
  machine-readable JSON", naming the observed case — when a command's response body is
  empty or not JSON, the CLI emits a structured non-success state rather than surfacing a
  raw decode-exception string as the caller's `error`.

## Impact

- Affected code (investigation targets): `cli/python/unity_puer_exec.py`
  (`run_cli` / the shared body-decoding path), `cli/python/unity_puer_exec_runtime.py`
  (the `failed` envelope construction), `cli/python/direct_exec_client.py`, and
  `cli/python/unity_session.py` where subprocess output is decoded.
- Affected behavior: how an empty or non-JSON response body is classified and reported for
  every formal command.
- Affected validation: `tests.test_unity_session_cli`, `tests.test_unity_puer_session`,
  `tests.test_direct_exec_client`, and the real-host case that surfaced it.
- No change to success payload shapes or to the exit-code assignments themselves.
