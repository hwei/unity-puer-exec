## 1. Implementation

- [ ] 1.1 Generalize `_resolve_exec_log_path` for all commands
- [ ] 1.2 Add `--start-offset` parameter to `wait-until-ready`
- [ ] 1.3 Inject `log_range` + `brief_sequence` on all exit paths of `wait-for-log-pattern`
- [ ] 1.4 Inject `log_range` + `brief_sequence` on all exit paths of `wait-for-result-marker`
- [ ] 1.5 Inject `log_range` + `brief_sequence` on all exit paths of `wait-until-ready`
- [ ] 1.6 Unit/integration tests covering the new output for each command's exit paths

## 2. Validation

- [ ] 2.1 Re-run the relevant help-only log-oriented baseline with Claude Haiku subagent and record whether final verification still falls back to direct `Editor.log` inspection after `unity_stalled`
- [ ] 2.2 Compare the new evidence against prior Prompt B records and summarize whether CLI-native post-stall verification improved
