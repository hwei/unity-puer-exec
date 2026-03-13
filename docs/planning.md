# Planning Rules

## Purpose

`docs/plans/` holds temporary execution context for substantial work.

Plans in this repository should be:

- executable from a fresh session
- readable by a subagent without replaying the full chat history
- small enough to avoid becoming a duplicate of long-lived docs

## Plan Types

This repository distinguishes three kinds of plans:

- `Governance Plan`
  - used when the main task is to change project-management documentation rather than final product artifacts
  - applies to governance-facing documents such as `AGENTS.md`, `docs/workflow.md`, `docs/planning.md`, `docs/roadmap.md`, `docs/status.md`, and `docs/decisions/`
  - may directly modify those long-lived governance documents as the task's primary output
  - should begin from explicit agreed constraints
  - should not leave governance-boundary or process-shaping choices to execution-time inference
- `Implementation Plan`
  - used when the main task is to change final product artifacts
  - applies to code, tests, and product-user-facing documentation such as `ReadMe.md`, CLI `--help`, package usage docs, and other user-facing contract docs
  - may also update governance-facing documents when implementation needs to distill or summarize results there
  - should treat key contract and behavior decisions as inputs, not open questions
- `Exploration Plan`
  - used when a critical unknown cannot yet be resolved through discussion alone
  - should define what to investigate, how to investigate it, what evidence to produce, and how that output constrains later plans

Plan type is determined by the task's main output, not merely by whether the task edits documentation or code.

If a task does not fit cleanly, prefer splitting it rather than mixing governance work, exploration, and implementation into one plan.

If a primarily governance task includes auxiliary changes that would directly alter final product behavior, test behavior, or product-user-facing documentation, split that work into an `Implementation Plan`.

If a governance task is too large or unstable for one task, its follow-up work should default to another `Governance Plan` unless the main output shifts to final product artifacts.

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

## Agreed Constraints

Plans that shape governance, behavior, or externally visible contracts must contain `Agreed Constraints`.

`Agreed Constraints` should record the key points that are already settled before execution begins. These are the constraints another executor must not reinterpret during implementation.

At minimum, treat these as pre-plan decisions when they affect downstream work:

- task boundaries
- user-visible parameters
- output or exit semantics
- command responsibilities
- lifecycle ownership
- compatibility direction for breaking or transitional behavior

If one of those items is still unresolved, do not hide it inside an implementation plan. Instead:

- resolve it in discussion first
- split an exploration task if execution is required to answer it
- or move it out of current scope and record it in roadmap or follow-up work

Open questions are allowed, but they must not change the current task's target behavior or downstream contract once implementation starts.

For `Governance Plan` tasks, the same rule applies to governance-boundary choices such as document authority, document role, entry ownership, and classification rules.

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

## Plan Shape

Plans should usually contain these sections:

- `Plan Type`
- `Scope`
- `Agreed Constraints`
- `Shared Context`
- `Requirements`
- `Work Items`
- `Open Questions`
- `Out Of Scope`
- `Integration`
- `Validation`
- `Risks`
- `Exit Criteria`

Use the smallest shape that still keeps the task executable from a clean context. For smaller tasks, some sections may be merged, but `Requirements`, `Validation`, and `Exit Criteria` should remain explicit when behavior is changing.

Template: `docs/plan-template.md`

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
