## Context

The current CLI help is good enough for successful completion, but the first validation round still showed extra probing before the agent settled on the main workflow. Improving efficiency now is a product-help problem, but it should be driven by durable transcript evidence rather than intuition alone.

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
The change should wait on transcript capture so help revisions can target real observed friction rather than maintainers' guesses.

Alternative considered:
- Improve help immediately from current summaries alone. Rejected because the existing evidence is useful but too coarse for confident optimization.

### Decision: Optimize for the first successful path
The help surface should emphasize the first correct workflow an agent should try for common project-scoped tasks, especially `exec` plus the minimal supporting observation or readiness steps.

Alternative considered:
- Add more comprehensive help without reprioritizing what appears first. Rejected because more help can still leave weaker agents exploring too broadly.

## Risks / Trade-offs

- [Efficiency gains may conflict with completeness] → Preserve deep help sections while making the top-level path more direct.
- [Observed friction may vary by task class] → Use transcript evidence from at least one simple and one longer task before changing the help contract.
- [Blocking on transcript capture delays optimization] → Accept the delay so later help changes are evidence-based and easier to validate.
