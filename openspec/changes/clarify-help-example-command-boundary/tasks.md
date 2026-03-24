## 1. Help Surface

- [ ] 1.1 Update top-level help wording so workflow-example names are clearly marked as `--help-example` targets rather than executable commands
- [ ] 1.2 Review related help sections to ensure command groups and workflow examples use non-overlapping phrasing

## 2. Prompt B Validation

- [ ] 2.1 Re-run Prompt B with `gpt-5.4-mini subagent`, using the published help surface only, and record whether the validating run still attempts to execute a workflow-example name as a subcommand
- [ ] 2.2 Compare the new subagent Prompt B transcript-backed evidence against the archived baseline and summarize whether help-example discoverability improved
