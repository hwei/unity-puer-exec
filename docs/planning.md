# Planning Rules

Use this file as the planning quickstart. Open `docs/planning-rules.md` only when you need deeper rationale or detailed authoring guidance.

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

For pointer-first shared context guidance, retrospective-use rules, and detailed subagent-friendly planning rules, see `docs/planning-rules.md`.
