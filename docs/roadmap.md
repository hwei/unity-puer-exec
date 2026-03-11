# Roadmap

## Rules

- Task IDs are hierarchical and stable, for example `T1`, `T1.2`, `T1.2.1`.
- Parent tasks are summary nodes by default.
- A child task belongs to exactly one parent task.
- A parent task is complete only when all direct child tasks that are not `draft` and not `dropped` are `done`.
- Same-level sibling tasks are linearly ordered by default. Higher same-level IDs depend on lower same-level IDs unless explicitly stated otherwise.
- Required task fields are:
  - `Status`
  - `Parent`
  - `Depends on`
  - `Done means`
- Supported task states are:
  - `draft`
  - `todo`
  - `in_progress`
  - `blocked`
  - `done`
  - `dropped`

## Active Work

## T1 Productize Repository Interface

- Status: todo
- Parent: none
- Depends on: none
- Done means: the repository can be consumed without relying on the migration-only skill skeleton layout

### T1.1 Define Repository-Facing Skill Entry

- Status: todo
- Parent: T1
- Depends on: none
- Done means: the repository has a stable repository-facing skill entry contract instead of relying on the current transitional README-only skill placeholder

### T1.2 Document Installation And Invocation Flow

- Status: todo
- Parent: T1
- Depends on: T1.1
- Done means: installation and invocation expectations are documented at the appropriate long-lived locations

### T1.3 Define End-To-End Validation Entry

- Status: draft
- Parent: T1
- Depends on: T1.2
- Done means: TBD
- Notes: The repository still lacks a normalized repo-level E2E entry after the initial migration.
