# Roadmap And Plan Governance Normalization

## Goal

Normalize how `unity-puer-exec` manages:

- roadmap task IDs
- roadmap task states
- roadmap update flow
- temporary execution plan filenames
- task-to-plan linkage

This round should leave the repository with one consistent rule set for task tracking and plan handling.

## Scope

In scope:

- update `docs/workflow.md` to define the roadmap update flow and the new plan filename rule
- update `docs/roadmap.md` to define the revised task state model and task fields
- update active roadmap entries to the new state vocabulary
- update any long-lived repository guidance that still describes the old plan naming rule or old task states

Out of scope:

- adding new product features
- changing decision archive contents unless required by the workflow normalization itself
- renaming historical commits

## Target Rules

### Roadmap task IDs

- Use task IDs in the form `T1`, `T1.2`, `T1.2.1`.
- `T` means `Task`.
- Dots indicate hierarchy only.
- Same-level numbering gives the default local planning order.
- Exact non-default dependencies must still be written in `Depends on`.

### Roadmap task fields

Each roadmap task should define:

- `Status`
- `Parent`
- `Depends on`
- `Plan`
- `Done means`

Optional fields such as `Notes` or `Blocked by` may be added when needed.

### Roadmap task states

Use this state set:

- `draft`
- `planning`
- `ready`
- `in_progress`
- `blocked`
- `done`
- `dropped`

State meanings:

- `draft`: issue recorded, scope not stable yet
- `planning`: accepted for further work, discussion or plan writing is underway
- `ready`: plan is confirmed and the task is ready to implement
- `in_progress`: implementation is underway
- `blocked`: implementation has started or is otherwise committed, but cannot currently complete
- `done`: implementation, validation, and distillation are complete
- `dropped`: explicitly not being pursued

`draft` tasks do not count toward parent completion.

### Parent task behavior

- Parent tasks are summary nodes by default.
- A child task belongs to exactly one parent task.
- A parent task is complete only when all direct child tasks that are not `draft` and not `dropped` are `done`.

### Roadmap update flow

- New issues discovered during implementation should first be added as `draft`.
- If the newly discovered issue is required to finish the current task, refine it under the current parent before implementation continues.
- If task scope, hierarchy, or dependencies change materially, update `docs/roadmap.md` before writing or revising the execution plan.
- When implementation starts, move the task to `in_progress`.
- When blocked, record the blocker in `docs/roadmap.md`, and in `docs/status.md` when it is actively affecting current work.
- When implementation is complete and stable conclusions have been distilled, mark the task `done`.

### Roadmap cleanup

- `docs/roadmap.md` is a live planning document, not a historical ledger.
- `done` and `dropped` are lifecycle states, not permanent archive states.
- After a completed or dropped task has had its stable conclusions distilled into long-lived documentation or source comments, it may be removed from `docs/roadmap.md`.
- `done` tasks should be kept only as long as needed to complete distillation and any immediate parent-task state updates.
- `dropped` tasks should be kept only when the reason for dropping them still needs to be captured and distilled elsewhere.

### Plan file naming

- Use filenames in the form `NNNN-Tx.y-short-slug.md`.
- `NNNN` is a 4-digit sortable sequence number, usually incremented by 10.
- Numbers indicate rough planning order, not exact execution history.
- Do not encode parent/child or dependency relationships in the sequence number itself.
- Insert new plans by choosing an unused number between neighbors when possible.
- If no gap exists, append a nearby higher number rather than renaming old plans.
- Deleted plan numbers are not reused.
- The slug should use short lowercase ASCII words joined by hyphens.

### Task-to-plan linkage

- An active roadmap task should name its current execution plan in the `Plan` field.
- A task may have `Plan: none` when it has not yet entered executable planning.
- One active task should have at most one active plan at a time.

## Implementation Steps

1. Update `docs/workflow.md` to replace the old plan naming guidance and add the roadmap update flow.
2. Update `docs/roadmap.md` to replace the old state model and required fields.
3. Rewrite existing active roadmap entries so they conform to the new field and state rules.
4. Update repository-level guidance such as `AGENTS.md` and `ReadMe.md` only if they still conflict with the new workflow wording.
5. Distill any stable governance conclusion into the long-lived docs above, then delete this plan file.

## Validation

I will verify this work by:

1. Reading `docs/workflow.md` and confirming it documents:
   - the discuss -> plan -> commit -> implement -> validate -> distill -> delete plan -> commit sequence
   - the roadmap update flow
   - the `NNNN-Tx.y-short-slug.md` filename rule
2. Reading `docs/roadmap.md` and confirming it documents:
   - the `draft/planning/ready/in_progress/blocked/done/dropped` state set
   - the required `Plan` field
   - the parent completion rule
   - the cleanup rule for removing distilled `done` and `dropped` tasks
3. Reading the active roadmap entries and confirming they use the new state vocabulary and include `Plan`.
4. Running `git diff --check` to catch formatting issues in the modified documentation.

## Acceptance Criteria

- No long-lived document in the repository still instructs contributors to name plan files only by task ID such as `T1.2-...`.
- `docs/workflow.md` and `docs/roadmap.md` describe one consistent model for task state transitions and roadmap maintenance.
- Active roadmap tasks are readable under the new model without requiring an extra mapping document.
- This plan can be deleted immediately after implementation because its stable conclusions have been distilled into the long-lived docs.
