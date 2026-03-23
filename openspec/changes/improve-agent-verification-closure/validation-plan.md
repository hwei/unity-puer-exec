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
- Cleanup status for repository-owned temporary host assets, including any remaining residue after the rerun batch

## Cleanup Step

- After the sequential rerun batch completes, run `python tools/cleanup_validation_host.py --project-path <PROJECT_PATH>`.
- Treat the cleanup tool as harness-owned workflow, not as part of the subagent task prompt.
- Record the cleanup result in the durable validation summary and per-track evidence.

## Second Slice Addendum

When the compile-recovery slice lands, reuse the same sequential rerun order and discovery constraints, but adjust the evaluation focus:

1. Prompt A remains the regression guardrail.
2. Standard Prompt C becomes the primary acceptance rail for the second slice.

### Second-Slice Evaluation Focus

The rerun should answer these questions:

1. Did Prompt A preserve the existing startup-continuity gains without regressing back to the old explicit readiness-recovery branch?
2. Did Standard Prompt C stop requiring a caller-authored refresh / compile / ready dance before the real verification exec?
3. If the compile-recovery path runs long, does the response stay on the normal `running + request_id -> wait-for-exec` path while exposing useful refresh-phase diagnostics?

### Second-Slice Track Expectations

#### Prompt A

- Expected role: regression guardrail only.
- A successful second-slice outcome preserves the current improved behavior even if Prompt A still remains `recoverable` for unrelated bridge or persistence-confirmation reasons.
- A regression includes falling back to the old pattern where the first task attempt again needs explicit `wait-until-ready` recovery before the main work can begin.

#### Standard Prompt C

- Preferred path: write the C# change, then use a later `exec --refresh-before-exec ...` style verification step rather than manually scripting refresh, compilation, and explicit readiness recovery as separate caller steps.
- `clean` means final verification stays inside the CLI surface and does not require the caller to author an extra refresh / compile / ready sequence outside the target verification exec.
- `recoverable` means final verification still stays inside the CLI surface, but the agent must branch into extra CLI recovery steps beyond the intended refreshed-exec path.
- `fallback` means final confirmation leaves the CLI surface for host-file or host-log inspection.

## Third Slice Addendum

When the compile-phase continuation slice lands, rerun the same two tracks sequentially with the same discovery restrictions.

### Third-Slice Evaluation Focus

The rerun should answer these questions:

1. Did Prompt A preserve the current startup-continuity behavior without regressing back to the old explicit readiness-recovery branch?
2. When Standard Prompt C uses `exec --refresh-before-exec`, does a compile-phase response now stay on the normal `running + request_id -> wait-for-exec` continuation path?
3. Did Standard Prompt C stop requiring a manual fallback to `wait-until-ready` after the first refreshed verification attempt?

### Third-Slice Track Expectations

#### Prompt A

- Expected role: regression guardrail only.
- A successful third-slice outcome preserves the current Prompt A behavior even if it remains `recoverable` for bridge-discoverability reasons.

#### Standard Prompt C

- Preferred path: write the C# change, then verify with `exec --refresh-before-exec ...`.
- If the request hits compile recovery, the caller-facing response should stay on `status = "running"` with `phase = "compiling"` and the normal `next_step`.
- `clean` means the agent can stay on `exec -> running/wait-for-exec -> completed` without branching to `wait-until-ready` after the refreshed verification attempt.
- `recoverable` means final verification still stays inside the CLI surface, but the agent must invent extra recovery beyond the intended refreshed-exec plus wait-for-exec path.
- `fallback` means final confirmation leaves the CLI surface for host-file or host-log inspection.
