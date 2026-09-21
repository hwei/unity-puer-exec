## 1. Root-Cause Investigation

- [ ] 1.1 Read the recovery-readiness path end to end (`ensure_session_ready`, `_has_recoverable_editor_signal`, the recovery wait loop, `_ensure_project_session_ready_after_refresh`, `unity_session_wait`, and the `wait-for-exec` resolution in `unity_puer_exec_runtime.py`) and map every site that can hold or re-probe a candidate endpoint. Verify: the map names the site that produced `no endpoint matched the target project yet` and whether it re-ran range-scan discovery.
- [ ] 1.2 Reproduce with mocked health transitions: a stale candidate endpoint (recorded pid dead or `/health` identity mismatch) while the requested project's Editor becomes ready on a later port in the range. Confirm whether the wait claims the later endpoint or stays `running`. Verify: the reproduction is deterministic and specific to the stale-candidate case.
- [ ] 1.3 Establish whether the environment preconditions matter (preferred port 55233/55231 already taken by another project, several unrelated Editors running) or whether the defect reproduces with a single instance. Verify: the finding states whether the multi-instance condition is a precondition or incidental.
- [ ] 1.4 Record the confirmed root cause in `design.md`'s Decisions section, replacing the placeholder text: which resolution step dropped the ready endpoint, and why. Verify: a reader can see the observed sequence, the rejected alternatives, and the evidence.

## 2. Fix and Regression Coverage

- [ ] 2.1 Implement the minimal fix at the identified site so a recovery wait re-runs range-scan discovery and claims a ready, project-matched endpoint instead of timing out on a stale candidate. Verify: the reproduction from 1.2 passes.
- [ ] 2.2 Add regression tests at the unit layer for the stale-candidate-then-ready-on-later-port transition. Verify: the regression fails without 2.1's fix.
- [ ] 2.3 Re-run the existing endpoint-identity and recovery coverage (`tests.test_unity_session`, `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_unity_puer_session`, `tests.test_cli_version`) to confirm no legitimate session reuse or misroute guard regresses. Verify: the "never claim another project's endpoint" guarantee still holds.
- [ ] 2.4 Confirm the fix does not turn a genuine "no endpoint will ever appear" case into an unbounded wait — a true terminal failure must still surface. Verify: a wait with no recoverable editor signal still returns its terminal outcome within the bounded budget.

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python suites relevant to endpoint resolution and readiness. Verify: green.
- [ ] 3.2 Confirm against the real host (`c3-client-tree2/Project`, see `openspec/specs/validation-host-integration/how-to-run.md`) with another project's Editor occupying a port in the range, and confirm the recovery wait claims the launched project's endpoint. Verify: the previously observed `no endpoint matched the target project yet` `running` timeout does not recur under the same staging.
- [ ] 3.3 Run `openspec validate diagnose-recovery-readiness-timeout` and confirm the change is archive-ready; revise the provisional delta if investigation concluded the durable text itself needs strengthening. Verify: the delta matches what the fix actually guarantees.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this defect from `diagnose-exec-missing-after-auto-refresh` and `diagnose-empty-response-parse-error`.
