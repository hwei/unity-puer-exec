## Purpose

Define the first rerun protocol after the initial Prompt A implementation slice lands.

## Rerun Order

1. Run Prompt A first.
2. Run Standard Prompt C second.
3. Run the two trials sequentially against the same Unity validation host project, not in parallel.

## Fixed Inputs

- Model: `gpt-5.4-mini subagent`
- Project path: the repository validation host from `.env` or explicit environment override
- CLI entry path: repository-local `cli/python/unity_puer_exec.py`

## Allowed Discovery Surface

- Published `unity-puer-exec` help surface
- Normal CLI execution against the target Unity project
- Publishable runtime artifacts produced during the task

## Disallowed Discovery Surface

- Product-repository source
- Product-repository tests
- OpenSpec change artifacts as task hints
- Maintainer command-level hints

## Prompt Sources

- Prompt A: reuse the archived wording exactly
- Standard Prompt C: use the wording in this change's [task-prompts.md](./task-prompts.md)

## Evaluation Focus

The rerun should answer two questions:

1. Did project-scoped `exec` for Prompt A stay inside the primary accepted request lifecycle more cleanly than before?
2. Did the same change keep the cleaner compile-and-call verification path for Standard Prompt C inside the CLI surface?

## Classification Rules

- `clean`: task success and final verification stayed inside the intended CLI surface without host-side fallback and without the extra recovery dance this change is targeting.
- `recoverable`: task success remained autonomous, but the agent still needed extra recovery, probing, or non-primary CLI branching before CLI-native verification succeeded.
- `fallback`: final confirmation depended on direct host-file or host-log inspection outside the intended CLI surface.

## Track-Specific Expectations

### Prompt A

- Preferred path: `exec --project-path ...` enters an accepted lifecycle and can continue with `wait-for-exec` when needed.
- A `clean` run should not require `wait-until-ready` as the normal recovery branch for the first task attempt.
- A `fallback` run includes host-scene-file inspection for final confirmation.

### Standard Prompt C

- Preferred path: write C# through `exec`, then verify with a later `exec` call returning the correct result.
- A `clean` run should not require host-file or host-log confirmation.
- Residual bridge-shape probing may still occur; if it stays minor and final confirmation remains CLI-native, classify based on the overall convergence rules rather than treating any single probe as automatic failure.

## Evidence To Retain

- Structured per-track record of help queries, key command trace, key outputs, and final classification
- Summary comparison against the latest committed baseline
- Raw transcript retention remains optional and temporary only
