## Why

`surface-play-mode-compile-block` made an `exec` that runs while the Editor is in play mode
with a pending compile-triggering change disclose a `compile_blocked` object and a
`compile_blocked_by_play_mode` warning. `wait-for-exec` recovers or continues that same
request and returns the same terminal result — but it does not compose the object or apply
the warning.

An agent whose request stays non-terminal and who continues with `wait-for-exec`
(`recover-exec-by-request-id`, the documented path) therefore loses the disclosure the
direct `exec` would have given it, and reads a plain `completed` that silently ran against
stale code. The recovery surface is the one most likely to be used when the first response
was ambiguous, so it is the worst place for the signal to be missing.

## What Changes

- Apply the same play-mode compile-block composition and warning transition to the
  `wait-for-exec` terminal response path that `exec` already uses.
- Keep the existing precedence rules: a failure status or an existing async warning keeps
  its code, and the `compile_blocked` object is attached in every case.
- Reuse the one runtime helper rather than duplicating the composition.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `import-change-refresh`: adds a requirement that a `wait-for-exec` response covering a
  request that hit a play-mode skip with a pending change carries the same
  `compile_blocked` disclosure and warning as the equivalent `exec` response.

## Impact

- `cli/python/unity_puer_exec_runtime.py`: the `wait-for-exec` terminal path calls the
  shared play-mode composition helper.
- `tests/test_unity_session_cli.py`: unit coverage for the recovered/continued case.
- `tests/test_real_host_integration.py`: the play-mode real-host case may assert the
  `wait-for-exec` recovery path.
- No new protocol field; the server already returns `refresh.skipped_reason` and
  `refresh.paths_changed` on the underlying exec.
