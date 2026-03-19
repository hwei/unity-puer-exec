## 1. Contract Definition

- [ ] 1.1 Define the machine-facing CLI behavior for project-scoped modal-dialog blockers in readiness and execution workflows.
- [ ] 1.2 Define the first real-host validation scenario for a reproducible modal blocker such as an unsaved-scene save prompt.

## 2. Runtime Detection And Reporting

- [ ] 2.1 Identify the narrowest reliable signal available to detect or strongly infer the targeted Unity modal blocker during project-scoped workflows.
- [ ] 2.2 Implement blocker reporting or blocker diagnostics in the project-scoped session/runtime path without regressing existing readiness and execution behavior.
- [ ] 2.3 Update CLI help or status guidance if a new blocker state becomes branchable.

## 3. Validation

- [ ] 3.1 Add or update real-host validation coverage for the targeted modal blocker scenario.
- [ ] 3.2 Verify the CLI reports the blocker outcome distinctly from a generic timeout or unrelated execution failure.
- [ ] 3.3 Summarize any remaining unsupported dialog classes and leave the change archive-ready.
