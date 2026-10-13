## 1. Audit the call sites

- [x] 1.1 For each of the seven `invoke_command` call sites, record what the command should report when the endpoint resets. Verify: the table states an expectation per call site, not a blanket claim.
- [x] 1.2 Confirm by reading each enclosing function that no call site swallows or reclassifies the reset into something the top-level envelope would render as a generic failure. Verify: the audit names the function, not just the line.

## 2. Coverage

- [x] 2.1 Add command-level coverage asserting a reset produces a structured, correctly classified result on each command path. Verify: the assertion is at the command layer, not a re-assertion of the exception-to-status mapping. `play` is already covered by `test_play_recovers_from_a_peer_reset_inside_the_bound` and `test_play_reset_for_the_whole_bound_exits_with_the_not_available_code`; this task covers the remaining paths.
- [x] 2.2 Add coverage distinguishing "the boundary classifies a reset" from "the command recovers from a reset", so a failure points at the right layer. Verify: both layers are separately asserted.
- [x] 2.3 Record any call site found to need a contract genuinely different from the others, as a finding rather than widening the shared boundary to fit. Verify: any such finding names the call site and the reason.

## 3. Closeout

- [x] 3.1 Run the default suite and confirm no regression.
- [x] 3.2 Run `openspec validate classify-peer-reset-on-all-transport-callers --strict` and `openspec validate --all`.
- [x] 3.3 Complete the apply closeout review, recording whether the audit found anything that should have been a spec delta.