## Why

A base-url `exec` whose automatic-refresh cycle does not settle within the CLI's budget
returns a non-terminal response that names a `request_id` and points the caller at
`wait-for-exec --request-id` as the continuation:

```
exit 10, status "running", phase "refreshing", request_id R
next_steps: [{command: "wait-for-exec",
              when: "you want to continue waiting for the accepted request to finish"}]
```

That continuation cannot work. The server emits the refreshing phase **before**
`TryAcceptExecRequest`, so no record for R exists server-side -- by construction, not because
a reload wiped it -- and base-url mode writes no client-side record either (every
pending-artifact read/write is gated on `selector == "project_path"`). `wait-for-exec
--base-url --request-id R` therefore answers a non-recoverable `missing`, while the response
just told the caller it was continuing an *accepted* request.

`diagnose-exec-missing-after-auto-refresh` closed the deterministic path into this state
(the settle budget was derived from `--wait-timeout-ms`) but deliberately left the `missing`
classification and the branch structure alone. The branches where a settle genuinely does
not complete -- and the branch where the single permitted resubmit is answered `compiling`
-- still hand the caller a promise the CLI cannot keep. That contradicts "Automatic refresh
is a non-terminal phase of the accepted exec request", whose intermediate-phase scenario
requires the response to make the continuation explicit **so the caller can wait for the
eventual script result**; a continuation that answers `missing` is not that.

## What Changes

- Confirm which non-terminal base-url branches still lead to a request whose record exists
  nowhere, and what each currently returns.
- Make the continuation real for a base-url request whose refresh has not settled: either
  keep resubmitting in-process until the script runs, or carry a client-side record that
  `wait-for-exec --base-url` can replay. Which one is a design decision, not assumed here.
- Define the exhausted-budget outcome: a terminal state that names the exhaustion and the
  resubmit path, never a `missing` for a request the CLI itself left unsettled.
- Keep genuinely absent/expired records reporting `missing` -- this change must not silence
  the status wholesale.
- Regression coverage first at the unit layer (the clock-modelled settle harness already
  exists), plus a real-host confirmation across a real reload.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds one scenario to "Automatic refresh is a non-terminal phase of
  the accepted exec request" naming the base-url continuation case -- while a base-url
  request's refresh has not settled, its documented continuation must converge on the script
  result rather than answering `missing`. Does not change the requirement's normative text.

## Impact

- Affected code (investigation targets): `cli/python/unity_puer_exec_runtime.py`
  (`_run_exec_impl` refresh loop and its `settled is None or refresh_attempts >= 1` bail-out,
  `_run_wait_for_exec_impl` base-url branch, `_running_or_timed_out_response`), and
  `cli/python/unity_puer_exec_surface.py` / `cli/python/help_surface.py` if the continuation
  guidance changes.
- Affected behavior: what a base-url `exec` returns when its own refresh has not settled, and
  whether `wait-for-exec --base-url --request-id` can continue such a request.
- Affected validation: `tests.test_unity_session_cli` (land the regression beside
  `AutomaticRefreshBaseUrlTests`) and the real-host refresh cases that exercise a real reload.
- No change to the settle budget, the server's refresh decision, or the accepted-job
  lifecycle once a job is accepted.
