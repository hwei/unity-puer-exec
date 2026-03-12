# Roadmap

## Rules

- Task IDs are hierarchical and stable, for example `T1`, `T1.2`, `T1.2.1`.
- `T` means `Task`.
- Dots indicate hierarchy only.
- Parent tasks are summary nodes by default.
- A child task belongs to exactly one parent task.
- A parent task is complete only when all direct child tasks that are not `draft` and not `dropped` are `done`.
- Same-level sibling tasks are linearly ordered by default. Higher same-level IDs depend on lower same-level IDs unless explicitly stated otherwise.
- Required task fields are:
  - `Status`
  - `Parent`
  - `Depends on`
  - `Plan`
  - `Done means`
- Supported task states are:
  - `draft`
  - `planning`
  - `ready`
  - `in_progress`
  - `blocked`
  - `done`
  - `dropped`
- `draft` means the issue is recorded but the scope is not stable yet.
- `planning` means the task has been accepted for further work and discussion or plan writing is underway.
- `ready` means the task has a confirmed plan and can begin implementation.
- `in_progress` means implementation is underway.
- `blocked` means the task cannot currently complete.
- `done` means implementation, validation, and distillation are complete.
- `dropped` means the task is explicitly not being pursued.
- `draft` tasks do not count toward parent completion.
- `docs/roadmap.md` is a live planning document, not a historical ledger.
- `done` and `dropped` tasks may be removed after their stable conclusions have been distilled into long-lived documentation or source comments.

## Active Work

## T1 Productize Repository Interface

- Status: planning
- Parent: none
- Depends on: none
- Plan: none
- Done means: the repository can be consumed without relying on the migration-only skill skeleton layout

### T1.1 Define Repository-Facing Skill Entry

- Status: planning
- Parent: T1
- Depends on: none
- Plan: none
- Done means: the repository has a stable repository-facing skill entry contract instead of relying on the current transitional README-only skill placeholder

### T1.2 Document Installation And Invocation Flow

- Status: planning
- Parent: T1
- Depends on: T1.1
- Plan: none
- Done means: installation and invocation expectations are documented at the appropriate long-lived locations

### T1.3 Define End-To-End Validation Entry

- Status: draft
- Parent: T1
- Depends on: T1.2
- Plan: none
- Done means: TBD
- Notes: The repository still lacks a normalized repo-level E2E entry after the initial migration.
