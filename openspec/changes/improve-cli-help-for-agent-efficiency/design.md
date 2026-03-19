## Context

Archived change `validate-help-only-agent-cli-discoverability` established the baseline: a `gpt-5.4-mini subagent` could complete both a simple scene-editing task and a longer code-write-plus-verification task using only the published `unity-puer-exec` help surface. That means discoverability is already above the success threshold for medium-capability agents.

That same baseline also showed the remaining problem: the subagent still explored a few secondary commands before converging on the shortest successful workflow. Improving efficiency is therefore a product-help problem, not a proof-of-capability problem.

The later archived change `capture-agent-cli-validation-transcripts` exists because the first-round validation preserved only summary-level evidence. Transcript capture is the prerequisite that lets this change target real observed friction points instead of inferring them from coarse summaries alone.

## Goals / Non-Goals

**Goals:**
- Make the shortest effective project-scoped workflow easier for medium-capability agents to discover quickly.
- Reduce help-driven branching into secondary commands when the task is a straightforward execution workflow.
- Validate that help changes improve convergence quality, not just eventual task success.

**Non-Goals:**
- Do not change the core CLI command model unless help changes prove insufficient.
- Do not optimize for `--base-url` in this pass.
- Do not proceed without transcript-backed evidence from prior validation runs.

## Decisions

### Decision: Block this work on transcript capture
The change should wait on transcript capture so help revisions can target real observed friction from the already-successful help-only subagent runs rather than maintainers' guesses.

Alternative considered:
- Improve help immediately from current summaries alone. Rejected because the existing evidence is useful but too coarse for confident optimization.

### Decision: Optimize for the first successful path
The help surface should emphasize the first correct workflow an agent should try for common project-scoped tasks, especially `exec` plus the minimal supporting observation or readiness steps, because the earlier subagent validation already proved the CLI is usable once that path is found.

Alternative considered:
- Add more comprehensive help without reprioritizing what appears first. Rejected because more help can still leave weaker agents exploring too broadly.

## Risks / Trade-offs

- [Efficiency gains may conflict with completeness] → Preserve deep help sections while making the top-level path more direct.
- [Observed friction may vary by task class] → Use transcript evidence from at least one simple and one longer task, matching the earlier help-only subagent validation set, before changing the help contract.
- [Blocking on transcript capture delays optimization] → Accept the delay so later help changes are evidence-based and easier to validate.
