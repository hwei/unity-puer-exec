## 1. Cleanup Scope

- [x] 1.1 Identify the current repository-owned validation temp roots and file patterns used in the host Unity project
- [x] 1.2 Decide where the cleanup inventory lives in repository-owned workflow code so it can be reused across reruns

## 2. Harness Cleanup Implementation

- [x] 2.1 Add a harness-owned cleanup step that removes declared validation-temp assets after rerun workflows complete
- [x] 2.2 Ensure the cleanup step runs for both successful and failed validation runs without relying on subagent-authored teardown
- [x] 2.3 Add residue verification so the harness can distinguish full cleanup from partial cleanup failure

## 3. Durable Evidence

- [x] 3.1 Extend validation result writing so cleanup status and remaining residue are recorded in durable OpenSpec evidence
- [x] 3.2 Update any repository-owned rerun documentation or helper flows to describe the harness-owned cleanup policy

## 4. Validation

- [x] 4.1 Run a representative rerun workflow that creates temporary host assets and confirm the harness removes them afterward
- [x] 4.2 Confirm the recorded validation evidence reports cleanup outcome correctly for the exercised run
