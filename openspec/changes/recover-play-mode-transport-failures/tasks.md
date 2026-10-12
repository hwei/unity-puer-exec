# Tasks

## 1. Reproduce and pin the current behavior

- [x] 1.1 Write a focused unit reproduction that drives the play-mode command envelope with a transport whose `play-mode` POST returns an empty body (an empty/unparseable response). Verify: it fails on current code — the command reports a terminal generic failure (or the dropped response) instead of recovering or preserving the formal state.
- [x] 1.2 Confirm the retry branch in `_post_play_mode` is unreachable today: `_parse_response_body` returns the boundary payload for an empty body, so the loop returns before re-resolving. Verify: the reproduction shows exactly one `play-mode` POST and no re-resolution.
- [x] 1.3 Confirm the exit-code collapse: a non-ok `play-mode` body (`empty_response`, `modal_blocked`) reaches `play` / `pause` / `stop` as exit `1`. Verify: the reproduction asserts the caller-visible exit code.

## 2. Implement recovery and exit-code fidelity

- [x] 2.1 Expose the client's status-to-exit-code mapping as a public `direct_exec_client.status_to_exit_code(payload)` (thin wrapper or rename over `_status_to_exit_code`), keeping behavior identical. Verify: existing `tests.test_direct_exec_client` stays green.
- [x] 2.2 In `_post_play_mode`, retry only the transport family (`status` of `empty_response` or `not_available`, or no parseable body) by re-resolving via `_play_probe_endpoint` until the existing `timeout_seconds` deadline; return every other parseable body immediately. Verify: reproduction 1.1 observes a retry and a recovered result.
- [x] 2.3 When the recovery bound elapses, return the structured non-success state (named status, operation, exit-code meaning) with its formal exit code instead of `None` / a generic failure. Verify: reproduction reports the structured state and exit code 12.
- [x] 2.4 In `_run_play_mode_command`, map a non-ok body status to its formal exit code via 2.1 while preserving the `invalid_play_state` and `_play_mode_absent` (`http_status == 404`) branches. Verify: `modal_blocked` -> 19, `empty_response` -> 12, `invalid_play_state` -> 1.

## 3. Regression coverage and validation

- [x] 3.1 Add unit tests for: retry-then-recover on an empty body, bounded no-recovery returns the structured state, a recognized non-transport status is not retried, and the non-ok exit-code mapping. Verify: the retry test fails without 2.2 and the exit-code test fails without 2.4.
- [x] 3.2 Run the focused Python suites (`tests.test_unity_session_cli`, `tests.test_unity_puer_session`, `tests.test_direct_exec_client`) and the full default suite. Verify: green.
- [x] 3.3 Run `openspec validate recover-play-mode-transport-failures` and confirm the delta matches the implemented behavior; revise the delta if the implementation concluded a requirement needs strengthening.
- [x] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category.
