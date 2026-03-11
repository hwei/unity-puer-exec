# Repository Process And Documentation Normalization Plan

## Background

`unity-puer-exec` now has enough repository-local conventions that they should be normalized into a stable, explicit documentation system instead of being spread across ad hoc plan files, local discussions, and partially overlapping top-level documents.

The target is not just "more docs". The target is a documentation structure that:

- keeps execution rules stable for agents
- keeps current work visible without mixing it with historical detail
- keeps temporary plans disposable
- keeps architectural decisions searchable
- keeps the repository readable even after multiple iterations

## Goal

Normalize repository process and documentation around this structure:

```text
repo/
  AGENTS.md
  docs/
    workflow.md
    roadmap.md
    status.md
    decisions/
      0001-*.md
      0002-*.md
    decisions_archive/
      YYYY-MM.md
    plans/
      T1.2-*.md
      T1.2.1-*.md
  tests/
  ReadMe.md
```

This work should establish stable rules for:

- document responsibilities
- test directory placement and repository-level test entry points
- roadmap structure and task states
- parent/child completion semantics
- temporary plan lifecycle
- decision retention and archiving
- blocked work handling in a single-mainline workflow

## Planned Changes

### 1. Create the normalized documentation skeleton

Add or normalize:

- [AGENTS.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\AGENTS.md)
- [ReadMe.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\ReadMe.md)
- `docs/workflow.md`
- `docs/roadmap.md`
- `docs/status.md`
- `docs/decisions/`
- `docs/decisions_archive/`
- `docs/plans/`
- `tests/`

The repository should end in a state where these paths are the canonical structure, not aspirational placeholders.

### 2. Define strict document responsibilities

The normalization should assign one clear purpose to each long-lived document.

Target responsibilities:

- `ReadMe.md`
  - repository purpose
  - high-level directory overview
  - quick entry points only
  - minimal repository-level test entry points only
- `docs/workflow.md`
  - repository development workflow
  - required step order
  - plan creation / implementation / validation / distillation / cleanup rules
- `docs/roadmap.md`
  - future and active work only
  - dependency structure
  - task identity and completion semantics
- `docs/status.md`
  - current focus only
  - current blockers only
  - near-term next steps only
- `docs/decisions/`
  - active architectural or process decisions still in force
- `docs/decisions_archive/`
  - older decisions moved out of the active set
- `docs/plans/`
  - temporary execution plans only
- `tests/`
  - canonical repository-level test location
  - repository-level test entry points
  - detailed test caveats should stay close to the relevant test code

### 3. Define roadmap data model

`docs/roadmap.md` should support hierarchical task IDs and predictable dependency behavior.

Planned rules:

- task IDs are stable and hierarchical, for example:
  - `T1`
  - `T1.2`
  - `T1.2.1`
- parent tasks are summary nodes by default
- child tasks must belong to exactly one parent task
- parent task completion means:
  - all direct child tasks that are not `draft` and not `dropped` are `done`
- same-level sibling tasks are linearly ordered by default:
  - larger same-level IDs depend on smaller same-level IDs
- explicit `Depends on` is required only when:
  - overriding default sibling order
  - expressing a cross-branch dependency
  - enabling non-default parallel work

Each executable roadmap task should carry these fields:

- `Status`
- `Parent`
- `Depends on`
- `Done means`
- optional short `Notes`

### 4. Define task states

`docs/roadmap.md` should define a small but sufficient state model.

Planned states:

- `draft`
  - quick placeholder
  - scope still unclear
  - does not count toward parent completion
- `todo`
  - defined and ready to execute
- `in_progress`
  - currently being executed
- `blocked`
  - cannot be completed because of an unresolved dependency or external condition
- `done`
  - completed and validated
- `dropped`
  - intentionally abandoned and excluded from completion requirements

### 5. Define blocked-work policy

This repository currently uses a single-mainline workflow by default.

The normalization should explicitly define:

- `blocked` is a task state, not a branch strategy
- blocked work may still be committed to `main` if the intermediate result is:
  - stable
  - validated
  - useful on its own
- if the intermediate result is unstable or leaves the repository in a misleading half-migrated state:
  - preserve progress on a temporary branch instead
  - keep `main` clean
- blockers must be recorded in:
  - `docs/roadmap.md`
  - `docs/status.md` when currently relevant

### 6. Define plan lifecycle

`docs/plans/` should become strictly temporary.

Planned rules:

- create a plan before substantial work
- review and commit the plan first
- implement and validate second
- distill stable conclusions into long-lived documents
- delete the completed plan file
- commit the implementation and plan deletion together

Distillation targets may include:

- `ReadMe.md`
- `docs/workflow.md`
- `docs/roadmap.md`
- `docs/status.md`
- `docs/decisions/`
- source code comments, when the knowledge is code-local

`ReadMe.md` should only receive high-level stable conclusions such as repository purpose, top-level structure, and quick entry points.

### 7. Define decision retention and archiving

Planned rules for `docs/decisions/`:

- keep at most 8 active decision files in `docs/decisions/`
- when the active set would exceed 8:
  - move older decisions into monthly archive files under `docs/decisions_archive/`
- archive files should use monthly names such as:
  - `2026-03.md`

Each archived entry should preserve at least:

- decision ID
- title
- date
- status
- replacement relationship if superseded

### 8. Distill current repository knowledge into the new structure

During implementation, migrate current stable knowledge into the normalized destinations instead of duplicating it.

Expected migration direction:

- repository purpose and layout summary into `ReadMe.md`
- execution flow into `docs/workflow.md`
- current and upcoming work into `docs/roadmap.md`
- immediate current state into `docs/status.md`
- durable architecture/process choices into `docs/decisions/`
- repository-level test layout and test entry points into `tests/`
- code-local operational constraints, validation caveats, and test-specific warnings into source comments near the relevant implementation or tests

### 9. Normalize test placement

Testing should be part of the normalization instead of remaining an implicit sidecar under the current skill directory.

Planned outcomes:

- define `tests/` as the canonical repository-level test location
- decide which current tests should move from `.claude/skills/unity-puer-exec/tests/` into `tests/`
- keep detailed test-local warnings and caveats near the relevant test files
- keep only minimal test entry guidance in `ReadMe.md`
- avoid duplicating detailed test behavior into global repository documents when code-local comments are the better fit

## Validation Steps

The implementation will be validated by directly executing these checks.

### 1. Verify normalized structure exists

Check that all intended long-lived paths exist:

- `AGENTS.md`
- `ReadMe.md`
- `docs/workflow.md`
- `docs/roadmap.md`
- `docs/status.md`
- `docs/decisions/`
- `docs/decisions_archive/`
- `docs/plans/`
- `tests/`

### 2. Verify roadmap model is explicit

Check that `docs/roadmap.md` explicitly documents:

- hierarchical task IDs
- parent completion semantics
- default same-level dependency rule
- the state set including `draft` and `blocked`
- required task fields

### 3. Verify workflow is explicit

Check that `docs/workflow.md` explicitly documents this sequence:

1. discuss
2. write plan
3. commit plan
4. implement
5. validate
6. distill stable conclusions
7. delete completed plan
8. commit implementation

### 4. Verify blocked policy is explicit

Check that `docs/workflow.md` or `docs/roadmap.md` explicitly documents:

- when blocked progress may still be committed to `main`
- when a temporary branch should be used instead

### 5. Verify decision retention rule is explicit

Check that the documentation explicitly states:

- active decisions are capped at 8
- older decisions move into monthly archive files

### 6. Verify temporary plans remain temporary

Check that:

- the normalization implementation plan itself is deleted before the final implementation commit
- long-lived conclusions are moved into the normalized document set

### 7. Verify test placement is normalized

Check that:

- `tests/` exists as the canonical repository-level test location
- repository-level test entry points are visible from the normalized structure
- detailed test caveats remain near the relevant test code or source comments rather than being duplicated into global docs

## Acceptance Criteria

This plan is complete only when all of the following are true:

- the target document structure exists in the repository
- `tests/` exists as part of the normalized repository structure
- each long-lived document has a clear non-overlapping responsibility
- `docs/roadmap.md` defines hierarchical IDs, states, and completion rules
- `docs/workflow.md` defines the required working sequence including plan deletion after distillation
- blocked-work handling is documented
- decision retention and archiving rules are documented
- the current stable repository conventions have been distilled into the new structure
- this temporary plan file is deleted before the final implementation commit

## Commit Plan

After approval, execution will use two commits:

1. commit this plan document
2. implement the normalized structure, validate it, delete this plan document, and commit the final result
