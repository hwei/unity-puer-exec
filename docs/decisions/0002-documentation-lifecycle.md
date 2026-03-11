# 0002 Documentation Lifecycle

- Date: 2026-03-11
- Status: accepted

## Decision

Plans under `docs/plans/` are temporary execution artifacts. Stable conclusions must be distilled into long-lived documents or source comments before the completed plan is deleted.

## Rationale

- Keeping completed plans indefinitely turns execution history into duplicate documentation.
- Durable knowledge belongs in the smallest stable destination that matches its scope.
- Repository-level structure is easier to maintain when transient execution detail is removed after distillation.

## Consequences

- `ReadMe.md`, `docs/workflow.md`, `docs/roadmap.md`, `docs/status.md`, `docs/decisions/`, and code-local comments must carry the durable knowledge.
- Completed plans should be removed together with the implementation commit that makes them obsolete.
