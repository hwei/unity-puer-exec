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

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python suites relevant to `unity_puer_exec_runtime.py` and the exec lifecycle. Verify: green.
- [ ] 3.2 Confirm against the real host that a base-url `exec` interrupted across a real reload converges instead of answering `missing`, using the validation host and the reload-triggering pattern already in `tests/test_real_host_integration.py`. Verify: the confirmation crosses a real domain reload, not a mock, and the previously observed continuation failure is gone.
- [ ] 3.3 Run `openspec validate make-base-url-exec-refresh-recoverable` and confirm the change is archive-ready; revise the delta if investigation concluded the durable text needs different substance. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this continuation gap from the intermittent launch-recovery and CLI empty-response flakes, which are not part of this change.
