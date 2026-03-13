# Workflow

## Required Sequence

Repository work should follow this order:

1. discuss the target change
2. resolve key downstream-shaping decisions or explicitly split them into exploration work
3. write a plan under `docs/plans/`
4. get subagent review for the plan
5. get human review for the plan, then commit the plan
6. implement the change
7. validate the change directly
8. distill stable conclusions into long-lived documents or source comments
9. record retrospective findings in the active plan file for human review when execution reveals stable follow-up findings or workflow improvement ideas
10. get human disposition on any recorded retrospective findings
11. delete the completed plan file when no retrospective findings remain unresolved
12. commit the implementation together with the plan deletion

## Plan Rules

- Substantial work should start with a plan file.
- Plan authoring rules live in `docs/planning.md`.
- Planning starts after discussion has already produced the agreed constraints needed to keep execution deterministic.
- Plan type should follow the task's main output: use `Governance Plan` for project-management documentation, `Implementation Plan` for final product artifacts, and `Exploration Plan` for critical unknowns.
- Plan file names should use the form `Tx.y-short-slug.md`, for example:
  - `T1.2-repo-packaging.md`
  - `T1.2.1-test-fixture-cleanup.md`
- The task ID is the primary identifier for a plan file.
- Default to one active plan file per task.
- If a task genuinely needs multiple concurrent or alternative plans, keep the same task ID and add a short distinguishing suffix instead of inventing a global sequence.
- Plans are temporary execution artifacts, not durable documentation.
- The review sequence is subagent review first, then human review.
- Implementer self-review does not satisfy the subagent-review step or the human-review step by itself.
- If subagent review finds unresolved key decisions that affect task boundaries, parameters, outputs, or command responsibilities, the task should return to discussion or be split into exploration work. The agent should not resolve those decisions unilaterally just to satisfy review.

## Roadmap Maintenance

- `docs/roadmap.md` is a live planning document, not a historical ledger.
- Task IDs use the form `T1`, `T1.2`, `T1.2.1`, where `T` means `Task` and dots indicate hierarchy only.
- Same-level task numbering provides the default local planning order, while exact non-default dependencies must still be written in `Depends on`.
- New issues discovered during implementation should first be added as `draft`.
- If a newly discovered issue is required to finish the current task, refine it under the current parent before implementation continues.
- Material changes to task scope, hierarchy, or dependencies should be reflected in `docs/roadmap.md` before writing or revising the execution plan.
- Active roadmap tasks should record their current execution plan in a `Plan` field, or `Plan: none` when no executable plan exists yet.
- Completed roadmap tasks should keep a minimal pointer such as `Output: ...` to the long-lived location that holds the distilled result.
- `done` and `dropped` tasks may be removed from `docs/roadmap.md` after their stable conclusions have been distilled and any immediate parent-task state updates have been completed.

## Distillation Rules

Before deleting a completed plan, move stable conclusions into the right destination:

- `ReadMe.md` for repository purpose, structure, and quick entry points
- `docs/roadmap.md` for active and future work
- `docs/status.md` for current focus, blockers, and next steps
- `docs/decisions/` for active decisions still in force
- source comments when the knowledge is local to specific code or tests

## Retrospective Rules

Before deleting a completed plan, the agent should add a brief `Retrospective` section to the active plan file when execution reveals stable follow-up findings or workflow improvement ideas.

- Retrospective findings are discussion inputs, not automatic repository updates.
- The agent should not modify `docs/roadmap.md`, `docs/workflow.md`, `docs/planning.md`, or other long-lived process documents unilaterally based on retrospective findings.
- Each retrospective item should state the observation, why it matters, and the suggested next step.
- Retrospective items remain in the plan until a human explicitly disposes of them.
- Human disposition may accept, defer, reject, or split the finding into follow-up work.
- Accepted findings should be reflected in the appropriate long-lived artifact before the plan is deleted.
- Deferred findings should be preserved in an explicit repo-visible location chosen during human disposition.
- Rejected findings may remain only as disposed notes in the plan and do not require further repository changes.
- If a finding is split into follow-up work, the follow-up task and any required roadmap update should be created before the plan is deleted.
- If execution reveals no retrospective findings, the plan may be deleted without an additional retrospective review step.
- A completed plan should not be deleted while it still contains unresolved retrospective items.
- If a newly discovered issue is required to claim the current task is complete, the agent should raise it before treating the task as done.

## Truth Hierarchy

- Source code and tests are the final behavioral source of truth for this repository.
- Documentation exists to support planning, review, communication, and discovery.
- When documentation and observed code or test behavior disagree, fix the documentation or change the code and tests deliberately; do not treat stale prose as authoritative by itself.

## Validation Rules

- Mainline commits must leave the repository in a directly verifiable state.
- Validation should be executed by the implementer, not left as an implied manual follow-up.
- Repository-level tests live under `tests/`.

## Blocked Work

- `blocked` is a task state, not a branch strategy by itself.
- Blocked progress may still be committed to `main` when the intermediate state is stable, validated, and useful on its own.
- If the intermediate state is unstable or leaves the repository in a misleading half-finished state, preserve it on a temporary branch instead of committing it to `main`.
- Relevant blockers should be visible in `docs/roadmap.md` and, when currently active, in `docs/status.md`.
