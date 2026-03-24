## Why

Current repository planning surfaces can still present contradictory change-state signals. In one observed case, a change records `status: queued` in `meta.yaml`, repository backlog tooling treats that as raw backlog metadata, and `openspec list --json` reports the same non-archived change as workflow `in-progress`, leaving contributors to infer which answer is authoritative for the decision they are making.

## What Changes

- Record the concrete mismatch between raw repository metadata state, repository backlog views, and generic OpenSpec workflow state.
- Clarify which query surfaces are intended to answer raw metadata questions versus interpreted operator-facing workflow questions.
- Record the adjacent workflow-governance gap that backlog-oriented problem-recording changes can look artificially complete when their tasks surface has no intentional remaining gap.
- Capture a preferred follow-up direction for exposing both answers side by side instead of forcing agents or maintainers to guess.
- Keep this change exploratory and problem-focused rather than implementing query-tool changes immediately.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: change-query requirements should explicitly cover cases where `meta.yaml.status`, repository-local backlog views, and generic OpenSpec workflow status disagree.

## Impact

- Affects repository planning guidance and future change-query tooling decisions.
- Affects how backlog/problem-recording OpenSpec changes should express intentionally unresolved follow-up work.
- May later affect `tools/openspec_backlog.py`, repository-local wrappers around OpenSpec queries, or other diagnostic query surfaces.
- Does not yet change product CLI behavior or repository backlog recommendation semantics by itself.
