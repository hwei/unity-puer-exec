# Planning Rules

## Purpose

`docs/plans/` holds temporary execution context for substantial work.

Plans in this repository should be:

- executable from a fresh session
- readable by a subagent without replaying the full chat history
- small enough to avoid becoming a duplicate of long-lived docs

## Plan File Naming

Use the task ID as the primary filename anchor:

- default form: `Tx.y-short-slug.md`
- default assumption: one active plan per task
- if a task truly needs multiple concurrent or alternative plans, keep the same task ID and add a short suffix

Do not use a repository-wide planning sequence. Plan files are temporary, and their identity should remain derivable from the roadmap task ID even after older plans are deleted.

## Pointer-First Shared Context

Use `Shared Context` to capture only the stable facts another executor must know before acting.

Prefer pointers over copied prose:

- point to `docs/roadmap.md` for task structure and status
- point to `docs/decisions/` for durable decisions
- point to specific source files or tests when the local code context matters

Only copy information into `Shared Context` when one of these is true:

- the fact is required immediately to execute the task
- opening the pointer alone would still leave important ambiguity
- the plan needs a tiny distilled summary to keep a work item executable in isolation

Do not use `Shared Context` to mirror large chunks of existing docs or chat history.

## OpenSpec-Inspired Rules

This repository does not adopt OpenSpec wholesale, but it intentionally borrows a small subset of its strengths:

- keep change context in repo-visible artifacts instead of relying on a single chat thread
- describe externally visible behavior in terms of requirements and scenarios, not only code edits
- keep change intent, implementation work, and durable decisions distinct

In this repository, those ideas map to:

- `docs/plans/` for temporary change execution context
- `docs/roadmap.md` for active task structure and dependency state
- `docs/decisions/` for durable conclusions still in force
- source comments or tests for localized behavioral contracts

## Plan Shape

Plans should usually contain these sections:

- `Scope`
- `Shared Context`
- `Requirements`
- `Work Items`
- `Integration`
- `Validation`
- `Risks`
- `Exit Criteria`

Use the smallest shape that still keeps the task executable from a clean context. For smaller tasks, some sections may be merged, but `Requirements`, `Validation`, and `Exit Criteria` should remain explicit when behavior is changing.

Template: `docs/plan-template.md`

## Subagent-Friendly Planning Rules

- Before a plan is submitted for human review, it should receive one clean-context subagent review that focuses on ambiguity, missing preconditions, and execution risk.
- `Shared Context` should stay pointer-first and should contain only stable facts another agent must know before acting.
- `Work Items` should be independently readable and should identify:
  - the goal
  - the expected write scope
  - whether the item can run in parallel
- `Integration` should name the owner responsible for combining outputs and resolving cross-item conflicts.
- `Validation` should state who verifies the result and whether validation is per-item or only after integration.
- Avoid plans that require an executor to infer hidden intent from chat history when that intent can be stated in one or two sentences inside the plan.
