## 1. Guidance

- [x] 1.1 Strengthen `exec` help so the required default-export entry shape is prominent for `--file`, `--stdin`, and `--code` script inputs
- [x] 1.2 Improve the `missing_default_export` failure message so it points to the expected minimal template

## 2. Prompt B Validation

- [x] 2.1 Re-run Prompt B with `gpt-5.4-mini subagent`, using published help only, and record whether first-pass file authoring still triggers `missing_default_export`
- [x] 2.2 Compare the new subagent Prompt B evidence against the archived baseline and the 2026-03-24 operator probe and summarize whether entry-shape discoverability improved
