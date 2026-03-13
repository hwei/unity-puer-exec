# Workflow

Use this file for the required repository sequence and for the default read path during planning and implementation.

## Required Sequence

Repository work should follow this order:

1. discuss the target change
2. resolve key downstream-shaping decisions or explicitly split them into exploration work
3. write a plan under `docs/plans/`
4. get subagent review for the plan
5. get human review for the plan, then commit the plan
6. implement the change
7. validate the change directly
8. distill stable conclusions by following `docs/workflow-closeout.md`
9. record retrospective findings in the active plan file for human review when execution reveals stable follow-up findings or workflow improvement ideas
10. get human disposition on any recorded retrospective findings
11. delete the completed plan file when no retrospective findings remain unresolved
12. commit the implementation together with the plan deletion

## Read Paths

- Fresh-session orientation:
  - start in `AGENTS.md`
  - then use `docs/index.md`
  - then `docs/status.md`
- Continuing active work:
  - start in `docs/status.md`
  - then `docs/roadmap.md`
  - then the active plan file when one exists
- Writing or revising a plan:
  - read this file first
  - then `docs/planning.md`
  - then `docs/plan-template.md`
  - open `docs/planning-rules.md` only when the quickstart points there
- Implementing an approved plan:
  - read this file first
  - then `docs/roadmap.md`
  - then the active plan file
- Closing out a completed task:
  - switch to `docs/workflow-closeout.md`
  - then the active plan file
  - then `docs/roadmap.md` only when a follow-up or output pointer must be updated

## Plan Rules

- Substantial work should start with a plan file.
- Planning quickstart lives in `docs/planning.md`.
- Deeper planning authoring rules live in `docs/planning-rules.md`.
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
