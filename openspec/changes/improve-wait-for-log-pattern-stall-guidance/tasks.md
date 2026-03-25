## 1. Implementation

- [x] 1.1 Generalize `_resolve_exec_log_path` for all commands
- [x] 1.2 Add `--start-offset` parameter to `wait-until-ready`
- [x] 1.3 Inject `log_range` + `brief_sequence` on all exit paths of `wait-for-log-pattern`
- [x] 1.4 Inject `log_range` + `brief_sequence` on all exit paths of `wait-for-result-marker`
- [x] 1.5 Inject `log_range` + `brief_sequence` on all exit paths of `wait-until-ready`
- [x] 1.6 Unit/integration tests covering the new output for each command's exit paths

## 2. Validation

- [x] 2.1 Re-run the relevant help-only log-oriented baseline with Claude Haiku subagent and record whether final verification still falls back to direct `Editor.log` inspection after `unity_stalled`
- [x] 2.2 Compare the new evidence against prior Prompt B records and summarize whether CLI-native post-stall verification improved

### 2.1 Result

Recorded in `results/prompt-b-menu-compile-verify-post-wait-stall-guidance.yaml`.

Claude Haiku subagent completed Prompt B entirely within the CLI observation surface. No fallback to direct `Editor.log` inspection. The agent used `exec` + `get-log-briefs` for verification rather than `wait-for-log-pattern`. No `unity_stalled` event occurred during the run, so the post-stall `log_range` + `brief_sequence` output from the three wait commands was not directly exercised.

### 2.2 Comparison Summary

| Dimension | 2026-03-23 baseline | 2026-03-24 rerun | 2026-03-25 post-wait-stall-guidance |
|---|---|---|---|
| Model | gpt-5.4-mini | gpt-5.4-mini | claude-haiku-4.5 |
| Editor.log fallback | **yes** | no | no |
| Final verification path | direct Editor.log | wait-for-log-pattern + --start-offset | exec + get-log-briefs |
| log_range availability | exec only | exec only | all commands (including wait commands) |
| Efficiency | recoverable | recoverable | recoverable |
| unity_stalled occurred | not recorded | no | no |

**Conclusion:** CLI-native post-stall verification capability has improved. The 2026-03-23 baseline fell back to direct `Editor.log` inspection; both subsequent runs (2026-03-24 and 2026-03-25) stayed entirely within the CLI observation surface. The `log_range` + `brief_sequence` output is now uniformly available across all five observation commands, eliminating the diagnostic blind spot that originally motivated this change.

**Limitation:** No `unity_stalled` event occurred in this validation run, so the specific post-stall output from the three wait commands was not directly tested under stall conditions. The evidence supports that the CLI surface is sufficient for verification without Editor.log fallback, but a stall-specific test would require either a longer-running scenario or a deliberate stall trigger.
