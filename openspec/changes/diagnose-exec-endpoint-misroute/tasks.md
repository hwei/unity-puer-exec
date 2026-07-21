## 1. Root-Cause Investigation

- [ ] 1.1 Read `unity_session.py`'s project-scoped discovery path end to end (`ensure_session_ready`, session-artifact reuse, preferred-port probing, range-scan discovery, post-launch/recovery waits) and map each site against the `formal-cli-contract` "Project-scoped commands validate control endpoint identity" requirement's scenarios.
- [ ] 1.2 Write a minimal unit reproduction with mocked health responses: requested project has no session artifact and is not running; a live endpoint on the preferred port reports `ready` health for a *different* project. Confirm whether current code claims/persists that endpoint for the requested project (reproducing the observed defect) or whether the mocked reproduction behaves correctly (meaning the real-host symptom had a different cause, e.g. environment state left over from an earlier run).
- [ ] 1.3 Separately investigate `get-log-source`'s observed default-log-path/preferred-port fallback behavior (seen when no session artifact exists yet) against the log-source-resolution contract to determine whether it is documented fallback behavior or a related defect. Record the conclusion in design.md before proceeding.
- [ ] 1.4 Record the confirmed root cause (or the confirmation that it could not be reproduced) in design.md's Decisions section, replacing the placeholder text.

## 2. Fix and Regression Coverage

- [ ] 2.1 Implement the minimal fix at the identified call site(s) so a live endpoint is never claimed or persisted for a project whose live health identity does not match the requested project, on any code path.
- [ ] 2.2 Add regression tests for the misroute scenario reproduced in 1.2.
- [ ] 2.3 Re-run the existing "valid artifact endpoint is reused" and "stale artifact endpoint is ignored" test coverage (or add it if missing) to confirm the fix does not regress legitimate session reuse.
- [ ] 2.4 If 1.3 found a related but distinct defect in scope, fix it and add its own regression coverage; if it is documented fallback behavior, note that conclusion and leave it unchanged.

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python test suites relevant to `unity_session.py` (`tests.test_unity_session`, `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_unity_puer_session`).
- [ ] 3.2 Optionally confirm the fix against the real host (`c3-client-tree2/Project`, see `openspec/specs/validation-host-integration/how-to-run.md`) if the mocked reproduction leaves residual doubt about real-world behavior.
- [ ] 3.3 Run `openspec validate diagnose-exec-endpoint-misroute --strict --no-interactive` and confirm all tasks and evidence are archive-ready. If investigation concluded the durable requirement text itself needs strengthening, revise the proposal to add a modified-capability delta and a spec file before archiving.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category.
