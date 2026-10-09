## 1. wait-for-exec discloses the block

- [ ] 1.1 Identify the exact terminal return points of `_run_wait_for_exec_impl` where the response is normalized and finalized, and where `_inject_guidance_into_response` is called. Verify: the finding lists the call site(s) and the non-terminal return paths that must be left alone.
- [ ] 1.2 Call the shared `_apply_play_mode_compile_block` on the terminal stdout/stderr immediately before guidance injection, mirroring `exec`. Verify: no new composition logic is introduced and the terminal response is the only one rewritten.
- [ ] 1.3 Confirm the `wait-for-exec` replay path already carries the server's `refresh.skipped_reason` / `refresh.paths_changed` so no protocol change is needed. Verify: the unit test observes the fields on the replayed response.

## 2. Guidance composition for the collision

- [ ] 2.1 Extend guidance composition so that the presence of a CLI-composed `compile_blocked` object on the response additionally selects the play-mode exit guidance, the same way the `version_mismatch` `guard` already selects a specific situation. Verify: `_attach_guidance` passes the CLI-owned presence into `help_surface`, and no script-authored `result` field is read.
- [ ] 2.2 Merge rather than replace: the emitted `situation` covers both the warning's own condition and the play-mode block; the emitted `next_steps` lead with the play-mode exit steps and preserve the warning's own follow-up (for async, `wait-for-result-marker`). Verify: the async-warning collision response contains both an exit step and the async follow-up.
- [ ] 2.3 Leave the single `warning` code unchanged and do not introduce a `warnings[]` shape. Verify: the response still reports `warning: "async_result_not_supported"` in the collision and no multi-warning field exists.
- [ ] 2.4 Apply the composition wherever the collision can occur (both `exec` and `wait-for-exec`), not only the new path. Verify: the merge lives in the shared composition, not in one command's branch.

## 3. Tests

- [ ] 3.1 Unit-test the continued case: a replayed exec terminal response with `refresh.skipped_reason: "play_mode"` and pending paths becomes `status: "warning"` with `warning: "compile_blocked_by_play_mode"` and a `compile_blocked` object. Verify: the test fails without 1.2.
- [ ] 3.2 Cover precedence: a recovered failure keeps its failure status and still carries the object; an async warning keeps `async_result_not_supported`.
- [ ] 3.3 Cover the async collision end to end: the response keeps `warning: "async_result_not_supported"`, carries the `compile_blocked` object, and its `situation` / `next_steps` include both the play-mode way out and `wait-for-result-marker`. Verify: the test fails without 2.2.
- [ ] 3.4 Cover the no-pending case (a play-mode skip with no pending paths is not rewritten) and the non-terminal case (a `running` / `refreshing` `wait-for-exec` response carries no `compile_blocked` object).
- [ ] 3.5 Update the play-mode real-host case (or add one) to continue via `wait-for-exec` and assert the same disclosure. Verify: green under the opt-in gate.

## 4. Help and validation

- [ ] 4.1 Confirm `wait-for-exec` status help and guidance describe the play-mode warning (reuse the `exec` wording where it applies). Verify: help-content tests assert it.
- [ ] 4.2 Run `tests.test_unity_session_cli` and the default Python suite. Verify: green.
- [ ] 4.3 Run `openspec validate disclose-play-mode-block-in-wait-for-exec`. Verify: green.
