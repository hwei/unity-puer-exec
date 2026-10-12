## Why

`_post_play_mode` documents that it "re-resolves a dropped endpoint within a bound",
but it cannot: `direct_exec_client.invoke_command` now returns a parseable JSON payload
even for an empty/unparseable response body, so `_parse_response_body` returns that
payload immediately and the retry branch is never reached. The reload edge that the
docstring intends to absorb is instead reported as terminal.

Worse, `_run_play_mode_command` re-wraps **any** non-ok body with a hard-coded exit code
`1`. So an `empty_response` (formal exit 12) or a `modal_blocked` (formal exit 19) from
the `play-mode` endpoint reaches a `play` / `pause` / `stop` caller as `exit 1`, losing the
formal exit-code contract that every other command family preserves. A transient
domain-reload drop during a play-mode transition therefore looks like an execution
failure rather than a retryable transport condition.

This was surfaced by the now-archived `diagnose-empty-response-parse-error` closeout as a
`product-improvement` follow-up.

## What Changes

- Make `_post_play_mode` treat a non-ok **boundary** result (`empty_response` /
  `not_available`, i.e. the endpoint dropped mid-reload) as a reload edge: re-resolve the
  endpoint and retry within the command's bound, as its docstring already claims, instead
  of returning it as a terminal result.
- When the bound elapses, return the structured boundary state with its **formal exit
  code**, not a collapsed `failed` / exit `1`.
- Stop `_run_play_mode_command` from hard-coding exit `1` for every non-ok body: map the
  body's status to the formal exit code (reusing the client's status-to-exit-code
  mapping) while preserving the existing special cases (`invalid_play_state`,
  `http_status == 404` / `play-mode` absent).
- No change to success payload shapes, to the play/pause/stop option surface, or to the
  play-mode transition semantics.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `play-mode-control`: adds a requirement that a play-mode command recovers a dropped
  control endpoint (for example an empty response body during a domain reload) by
  re-resolving and retrying within its bound, and that when recovery is not possible it
  reports the structured non-success state with its formal exit code rather than
  collapsing it into a generic failure.

## Impact

- Affected code: `cli/python/unity_puer_exec_runtime.py` — `_post_play_mode`,
  `_run_play_mode_command`, and the `_play_mode_absent` / `invalid_play_state` branches;
  `cli/python/direct_exec_client.py` if the status-to-exit-code mapping needs a public
  helper.
- Affected behavior: how a dropped or empty `play-mode` response is classified and how
  `play` / `pause` / `stop` report it, including its exit code.
- Affected validation: `tests.test_unity_session_cli` (play-mode command envelope tests)
  and a focused unit test for the retry/exit-code behavior.
- No change to the play-mode success contract or to the `exec` transport boundary.
