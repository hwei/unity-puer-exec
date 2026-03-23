## 1. Protocol Refresh

- [x] 1.1 Review the archived baseline prompts and validation summaries, then document the exact comparison inputs for this revalidation round
- [x] 1.2 Update OpenSpec validation guidance and any change-local prompts or recording templates needed for fixed-model, fixed-prompt baseline revalidation

## 2. Baseline Revalidation

- [x] 2.1 Run Prompt A with the published CLI help surface only, using `gpt-5.4-mini subagent` and sequential project usage
- [x] 2.2 Run Prompt B with the published CLI help surface only, using `gpt-5.4-mini subagent` and sequential project usage
- [x] 2.3 Record structured results for both runs, explicitly capturing help queries, command trace, task success, autonomy, efficiency, and environment-friction findings

## 3. Comparison And Closeout

- [x] 3.1 Compare the new baseline results against the archived pre-help and post-help evidence for Prompt A and Prompt B
- [x] 3.2 Summarize whether the current CLI baseline is clean, recoverable, or regressed for the basic workflows and identify any follow-up candidates before archive readiness
