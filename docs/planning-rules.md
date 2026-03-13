# Planning Rules Reference

Use this file only when `docs/planning.md` is not enough for the current planning task.

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

`Governance Plan` is the repository's plan type for changing those governance documents directly.

## Retrospective Use

A plan may gain a `Retrospective` section during or after execution.

Use it only for stable follow-up findings or workflow improvement ideas that need human review before they can affect long-lived planning or process documents.

Do not use `Retrospective` to reopen agreed constraints or to smuggle new implementation scope into the current task.

## Subagent-Friendly Planning Rules

- Before a plan is submitted for human review, it should receive one clean-context subagent review that focuses on ambiguity, missing preconditions, and execution risk.
- One required subagent-review check is whether the plan still contains key decisions that should have been resolved before planning.
- `Shared Context` should stay pointer-first and should contain only stable facts another agent must know before acting.
- `Work Items` should be independently readable and should identify:
  - the goal
  - the expected write scope
  - whether the item can run in parallel
- `Integration` should name the owner responsible for combining outputs and resolving cross-item conflicts.
- `Validation` should state who verifies the result and whether validation is per-item or only after integration.
- Avoid plans that require an executor to infer hidden intent from chat history when that intent can be stated in one or two sentences inside the plan.
- If subagent review finds unresolved key decisions, the default next step is to return to discussion or split an exploration task, not to let the implementing agent invent those decisions.
