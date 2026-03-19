## 1. Validation Protocol

- [x] 1.1 Write the first-round help-only validation protocol, including allowed and disallowed discovery surfaces.
- [x] 1.2 Define the standard task prompts for the simple scene-editing task and the longer code-change-plus-verification task.
- [x] 1.3 Define the result-recording format for `task_success`, `autonomy`, `efficiency`, and `discoverability_findings`.
- [x] 1.4 Define a baseline reset and cleanup procedure so repeated trials do not inherit prior editor state.

## 2. First-Round Execution

- [x] 2.1 Prepare the real-host validation environment and confirm the publishable CLI help surface is the only required discovery path.
- [x] 2.2 Run the simple scene-editing help-only agent task and record the outcome using the standard result format.
- [ ] 2.3 Run the longer compile-and-verify help-only agent task and record the outcome using the standard result format.

## 3. Findings and Follow-up

- [ ] 3.1 Summarize the first-round discoverability findings, separating CLI help gaps from unrelated runtime or environment issues.
- [ ] 3.2 Decide whether the findings justify a follow-up product/help improvement change or a later harness-automation change.
- [ ] 3.3 Update the change artifacts for archive readiness once the first-round validation and findings summary are complete.
