# Workflow

## Required Sequence

Repository work should follow this order:

1. discuss the target change
2. write a plan under `docs/plans/`
3. review and commit the plan
4. implement the change
5. validate the change directly
6. distill stable conclusions into long-lived documents or source comments
7. delete the completed plan file
8. commit the implementation together with the plan deletion

## Plan Rules

- Substantial work should start with a plan file.
- Plan file names should use the relevant task ID when possible, for example:
  - `T1.2-repo-packaging.md`
  - `T1.2.1-test-fixture-cleanup.md`
- Plans are temporary execution artifacts, not durable documentation.

## Distillation Rules

Before deleting a completed plan, move stable conclusions into the right destination:

- `ReadMe.md` for repository purpose, structure, and quick entry points
- `docs/roadmap.md` for active and future work
- `docs/status.md` for current focus, blockers, and next steps
- `docs/decisions/` for active decisions still in force
- source comments when the knowledge is local to specific code or tests

## Validation Rules

- Mainline commits must leave the repository in a directly verifiable state.
- Validation should be executed by the implementer, not left as an implied manual follow-up.
- Repository-level tests live under `tests/`.

## Blocked Work

- `blocked` is a task state, not a branch strategy by itself.
- Blocked progress may still be committed to `main` when the intermediate state is stable, validated, and useful on its own.
- If the intermediate state is unstable or leaves the repository in a misleading half-finished state, preserve it on a temporary branch instead of committing it to `main`.
- Relevant blockers should be visible in `docs/roadmap.md` and, when currently active, in `docs/status.md`.
