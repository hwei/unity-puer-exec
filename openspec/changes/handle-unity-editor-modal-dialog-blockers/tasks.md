## 1. Contract Definition

- [x] 1.1 Define the machine-facing CLI behavior for project-scoped modal-dialog blockers in execution workflows and explicit blocker queries.
- [x] 1.2 Define the first real-host validation scenarios for reproducible save-scene modal blockers.

## 2. Runtime Detection And Reporting

- [x] 2.1 Identify the narrowest reliable signal available to detect the targeted Unity modal blockers during project-scoped execution workflows.
- [x] 2.2 Implement blocker reporting or blocker diagnostics in the project-scoped session/runtime path without regressing existing readiness and execution behavior.
- [x] 2.3 Update CLI help or status guidance if a new blocker state becomes branchable.

## 3. Validation

- [x] 3.1 Add or update real-host validation coverage for the targeted modal blocker scenarios.
- [x] 3.2 Verify the CLI reports the blocker outcome distinctly from a generic timeout or unrelated execution failure.
- [x] 3.3 Summarize any remaining unsupported dialog classes and leave the change archive-ready.
