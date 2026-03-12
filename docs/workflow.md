# Workflow

## Required Sequence

Repository work should follow this order:

1. discuss the target change
2. write a plan under `docs/plans/`
3. get subagent review for the plan
4. get human review for the plan, then commit the plan
5. implement the change
6. validate the change directly
7. distill stable conclusions into long-lived documents or source comments
8. delete the completed plan file
9. commit the implementation together with the plan deletion

## Plan Rules

- Substantial work should start with a plan file.
- Plan authoring rules live in `docs/planning.md`.
- Plan file names should use the form `Tx.y-short-slug.md`, for example:
  - `T1.2-repo-packaging.md`
  - `T1.2.1-test-fixture-cleanup.md`
- The task ID is the primary identifier for a plan file.
- Default to one active plan file per task.
- If a task genuinely needs multiple concurrent or alternative plans, keep the same task ID and add a short distinguishing suffix instead of inventing a global sequence.
- Plans are temporary execution artifacts, not durable documentation.
- The review sequence is subagent review first, then human review.
- Implementer self-review does not satisfy the subagent-review step or the human-review step by itself.

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
