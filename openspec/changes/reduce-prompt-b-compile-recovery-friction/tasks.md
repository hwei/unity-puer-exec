## 1. Recovery Improvement

- [ ] 1.1 Identify the smallest product or help-surface change that can make the Prompt B write-compile-invoke sequence more deterministic after generating a C# script
- [ ] 1.2 Implement that change without mutating the archived Prompt B wording

## 2. Prompt B Validation

- [ ] 2.1 Re-run Prompt B with `gpt-5.4-mini subagent`, using published help only, and record whether the workflow still needs the same explicit compile-recovery step after writing the C# script
- [ ] 2.2 Compare the new subagent Prompt B evidence against the archived baseline and the 2026-03-24 records and summarize whether compile-recovery friction measurably decreased
