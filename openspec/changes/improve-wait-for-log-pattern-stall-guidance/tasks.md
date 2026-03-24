## 1. Stall-Recovery Improvement

- [ ] 1.1 Identify the smallest product or help-surface change that can make `wait-for-log-pattern` outcomes with `unity_stalled` easier to recover from without leaving the CLI surface
- [ ] 1.2 Implement that change with focused tests or transcript-backed evidence as appropriate

## 2. Validation

- [ ] 2.1 Re-run the relevant help-only log-oriented baseline with `gpt-5.4-mini subagent` and record whether final verification still falls back to direct `Editor.log` inspection after `unity_stalled`
- [ ] 2.2 Compare the new evidence against the 2026-03-24 archived Prompt B records and summarize whether CLI-native post-stall verification improved
