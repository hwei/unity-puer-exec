## 1. Contract Clarification

- [ ] 1.1 Publish the guaranteed `ctx` fields for `exec` scripts and explicitly avoid implying unsupported fields such as `project_path`
- [ ] 1.2 Add guidance or examples that show how project-local paths should be derived through supported Unity APIs when needed

## 2. Prompt B Validation

- [ ] 2.1 Re-run Prompt B with `gpt-5.4-mini subagent`, using published help only, and record whether the validation script path still assumes unsupported `ctx` fields
- [ ] 2.2 Compare the new subagent Prompt B evidence against the 2026-03-24 operator probe and summarize whether script-context misunderstandings decreased
