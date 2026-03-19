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

### Decision: Express command role hierarchy directly in help
The revised help surface should state command role hierarchy explicitly instead of leaving agents to infer priority from a flat command list. `exec` should be presented as the normal first command for project-scoped work, `wait-for-result-marker` and `wait-for-log-pattern` should appear as normal follow-up observation paths, `wait-until-ready` should be positioned as supporting readiness recovery, and `get-log-source` plus `ensure-stopped` should be marked as secondary or troubleshooting commands.

Alternative considered:
- Keep the existing command descriptions and only reorder the command list. Rejected because ordering alone still leaves role ambiguity and does not clearly tell medium-capability agents which commands are primary versus secondary.

## Implementation Notes

- Top-level help should add a short `Recommended Path` section before the broader command reference.
- Top-level command presentation should group commands by role so the primary project-scoped path is visible before secondary inspection or cleanup commands.
- Per-command quick-start text should use role-oriented language such as `normal first command`, `normal follow-up`, `supporting readiness`, or `secondary troubleshooting` so the preferred path remains visible in both top-level and deep help.
- Deep argument and status help should remain intact so the refinement shortens discovery time without weakening the formal CLI contract.

## Risks / Trade-offs

- [Efficiency gains may conflict with completeness] → Preserve deep help sections while making the top-level path more direct.
- [Observed friction may vary by task class] → Use transcript evidence from at least one simple and one longer task, matching the earlier help-only subagent validation set, before changing the help contract.
- [Blocking on transcript capture delays optimization] → Accept the delay so later help changes are evidence-based and easier to validate.
