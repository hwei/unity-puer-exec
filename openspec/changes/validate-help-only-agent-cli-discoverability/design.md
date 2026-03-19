## Context

`unity-puer-exec` now has a formal help surface with top-level workflows, per-command help, status help, and workflow examples. That surface is intended to be publishable, while repository source and tests are not. The immediate question is not whether the CLI can be automated by a highly informed maintainer, but whether a moderately capable agent can discover and operate the intended Unity Editor workflow from the published help alone.

This work belongs in OpenSpec validation artifacts rather than `openspec/project.md` because it defines a repeatable repository-owned validation protocol with durable pass criteria. It does not change repository-wide collaboration guidance and does not yet change the formal CLI contract.

## Goals / Non-Goals

**Goals:**
- Define a repeatable help-only validation protocol for real Unity Editor tasks.
- Constrain the first round to publishable discovery surfaces: CLI help plus actual CLI execution.
- Measure three distinct outcomes for each task: task success, autonomy, and efficiency.
- Capture discoverability findings in a way that can later drive product, help, or harness follow-up work.

**Non-Goals:**
- Do not add new CLI behavior or help text in this change.
- Do not require full harness automation in the first round.
- Do not treat Unity plugin source discovery as a required success path.
- Do not cover `--base-url` or deliberately constructed low-frequency failure scenarios in the first round.

## Decisions

### Decision: Start as a validation change, not a harness change
The first round will be a `validation` change. The main need is to define the protocol and run a small number of realistic trials, not to build automation before the gaps are known.

Alternative considered:
- Build a reusable harness immediately. Rejected for now because it would optimize automation before the task shapes and scoring criteria are proven useful.

### Decision: Restrict the discovery surface to published CLI help
The protocol will allow agents to use `unity-puer-exec --help`, subcommand help, `--help-args`, `--help-status`, `--help-example`, and actual CLI execution. Repository-only source and tests are excluded because they are not published to end users.

Alternative considered:
- Allow repository source as auxiliary context. Rejected because it would blur whether failures come from discoverability or from the agent simply not reading implementation details that real users never receive.

### Decision: Use real end-to-end tasks instead of synthetic command quizzes
The first round will validate complete Unity Editor outcomes, not just whether the agent can name commands. The initial task set will include one simple scene-editing task and one multi-step task that forces execution, compile/recovery waiting, and result verification.

Alternative considered:
- Validate only command selection. Rejected because command recall alone does not prove the CLI is actually operable in realistic workflows.

### Decision: Score autonomy separately from task success
Each task result will record:
- `task_success`: whether the real Unity-side outcome was achieved
- `autonomy`: whether the agent stayed inside the allowed discovery boundary
- `efficiency`: whether the agent converged cleanly, recoverably, or poorly
- `discoverability_findings`: what help or workflow gaps materially slowed or blocked progress

Alternative considered:
- Use a single pass/fail. Rejected because it cannot distinguish “worked, but only with excessive blind trial-and-error” from “worked cleanly from help.”

## Risks / Trade-offs

- [Task outcome may mix CLI discoverability with Unity API knowledge] → Keep the first task simple and phrase the second task around workflow integration, then record whether the blocker was CLI discovery or Unity-side authoring knowledge.
- [Manual validation can be noisy and hard to compare] → Standardize the task prompts, allowed tools, and scoring fields before running the first trial.
- [A validation-only change may stop short of durable regression coverage] → Treat this as the intake step; if the findings stabilize and repeat, promote the protocol into a harness follow-up change.
- [Real-host tasks can fail for reasons unrelated to discoverability] → Record runtime/environment blockers separately from help-surface findings so product problems are not misclassified as validation noise.
