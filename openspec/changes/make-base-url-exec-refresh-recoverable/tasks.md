## 1. Confirm the branches and choose the continuation design

- [ ] 1.1 Enumerate every path where a base-url `exec` returns non-terminal for a request the server has not accepted: the `settled is None` settle-timeout branch, the `refresh_attempts >= 1` branch, and a post-settle resubmit that the server answers `compiling`. Confirm for each whether it is reachable and what it currently returns. Verify: the inventory names each branch with its call site and emitted payload, and states which branch `diagnose-exec-missing-after-auto-refresh` already closed.
- [ ] 1.2 Establish that the `request_id` in that response has no record anywhere, and that `wait-for-exec --base-url --request-id` therefore answers `missing`. Verify: the finding is reproduced against the CLI (mocked transport is fine), not inferred from reading the server.
- [ ] 1.3 Decide between the two candidate designs in `design.md` Decision 1 -- in-process retry under the same `request_id`, or a client-side record that `wait-for-exec --base-url` can replay. Verify: the decision names the chosen option, rules out the alternative with evidence, and says whether the advertised `next_steps` change.
- [ ] 1.4 Define the exhausted-budget outcome and the resubmit-safety invariant. Verify: the outcome is a real terminal state (not `missing`), carries a `next_steps` resubmit path, and the stated invariant shows a resubmit cannot double-run a script that already ran.
- [ ] 1.5 Write a deterministic reproduction for the chosen branch by extending the clock-modelled settle harness in `tests/test_unity_session_cli.py::AutomaticRefreshBaseUrlTests`. Verify: it fails on current code and asserts on the caller-visible response, not on an internal call count alone.
- [ ] 1.6 Record the confirmed behavior and the chosen design in `design.md`'s Decisions section, replacing the placeholder text. Verify: a reader can see which branch is fixed, what the exhausted-budget outcome is, and why the alternative was rejected.

## 2. Implement the continuation and cover it

- [ ] 2.1 Implement the chosen design so a non-terminal base-url refresh phase keeps the request continuable and the terminal response carries the script result. Verify: the reproduction from 1.5 passes, and no accepted-job status changes shape.
- [ ] 2.2 Make the emitted guidance match reality: the response must not advertise `wait-for-exec --request-id` as the continuation for a request whose record exists nowhere. Verify: the guidance surface names only continuations that work for the chosen design.
- [ ] 2.3 Add regression coverage for the branch(es) fixed in 2.1, including the exhausted-budget outcome. Verify: each regression fails without 2.1's fix.
- [ ] 2.4 Re-run the exec lifecycle coverage (`tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_response_file_output`) and confirm genuinely absent or expired records still report non-recoverable `missing`. Verify: the durable contract still holds for the cases it was written for, and `missing` was not silenced.

## 3. State the settle budget on the help surfaces

- [ ] 3.1 Read the `exec` help surface end to end (`cli/python/help_surface.py`: the option list, the "Automatic refresh" line, "Timeout Rules", and the `--help-status` status section) and name every sentence from which a caller could infer that `--wait-timeout-ms` bounds an automatic refresh's settle. Confirm the two budgets in code (`--wait-timeout-ms` in `_run_exec_impl` / `direct_exec_client`, and `_post_refresh_ready_timeout_seconds`). Verify: the finding lists the exact sentences per surface and cites both call sites.
- [ ] 3.2 Enumerate the existing help-content assertions that touch these strings so none is relaxed to make room for the new text. Verify: the list names each test case and the guarantee it holds.
- [ ] 3.3 Add the statement to `exec --help` in the wait/timeout guidance as well as the automatic-refresh line, worded for the continuation chosen in 1.3 (design Decision 4, no literal number). Make `exec --help-status` consistent, and leave `wait-for-compile --settle-timeout-seconds` describing the same cycle. Verify: `exec --help` read as plain text carries both facts, and neither status nor `wait-for-compile` help contradicts it.
- [ ] 3.4 Add regression assertions on the new statement to the help-content tests, and review each pre-existing assertion from 3.2 rather than deleting any. Verify: the new assertions fail without 3.3, and no pre-existing help guarantee was dropped.

## 4. Validation and Closeout

- [ ] 4.1 Run the focused Python suites relevant to `unity_puer_exec_runtime.py`, the exec lifecycle, and the help surfaces (`tests.test_unity_session_cli`, `tests.test_cli_version`, `tests.test_openspec_spec_hygiene`). Verify: green.
- [ ] 4.2 Capture the `exec --help` and `exec --help-status` output as evidence. Verify: the transcript shows the settle-budget statement and the corrected continuation guidance without running the CLI.
- [ ] 4.3 Confirm against the real host that a base-url `exec` interrupted across a real reload converges instead of answering `missing`, using the validation host and the reload-triggering pattern already in `tests/test_real_host_integration.py`. Verify: the confirmation crosses a real domain reload, not a mock, and the previously observed continuation failure is gone.
- [ ] 4.4 Run `openspec validate make-base-url-exec-refresh-recoverable` and confirm the change is archive-ready; revise the delta if investigation concluded the durable text needs different substance. Verify: the delta matches the implemented behavior.
- [ ] 4.5 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this continuation and help gap from the intermittent launch-recovery and CLI empty-response flakes, which are not part of this change.
