## 1. Implementation

- [ ] 1.1 Identify the exact terminal return points of `_run_wait_for_exec_impl` where the response is normalized and finalized, and where `_inject_guidance_into_response` is called. Verify: the finding lists the call site(s) and the non-terminal return paths that must be left alone.
- [ ] 1.2 Call the shared `_apply_play_mode_compile_block` on the terminal stdout/stderr immediately before guidance injection, mirroring `exec`. Verify: no new composition logic is introduced and the terminal response is the only one rewritten.
- [ ] 1.3 Confirm the `wait-for-exec` replay path already carries the server's `refresh.skipped_reason` / `refresh.paths_changed` so no protocol change is needed. Verify: the unit test observes the fields on the replayed response.

## 2. Tests

- [ ] 2.1 Unit-test the continued case: a replayed exec terminal response with `refresh.skipped_reason: "play_mode"` and pending paths becomes `status: "warning"` with `warning: "compile_blocked_by_play_mode"` and a `compile_blocked` object. Verify: the test fails without 1.2.
- [ ] 2.2 Cover precedence: a recovered failure keeps its failure status and still carries the object; an async warning keeps `async_result_not_supported`.
- [ ] 2.3 Cover the no-pending case: a play-mode skip with no pending paths is not rewritten.
- [ ] 2.4 Cover the non-terminal case: a `running` / `refreshing` `wait-for-exec` response carries no `compile_blocked` object.
- [ ] 2.5 Update the play-mode real-host case (or add one) to continue via `wait-for-exec` and assert the same disclosure. Verify: green under the opt-in gate.

## 3. Help and validation

- [ ] 3.1 Confirm `wait-for-exec` status help and guidance describe the play-mode warning (reuse the `exec` wording where it applies). Verify: help-content tests assert it.
- [ ] 3.2 Run `tests.test_unity_session_cli` and the default Python suite. Verify: green.
- [ ] 3.3 Run `openspec validate disclose-play-mode-block-in-wait-for-exec`. Verify: green.
