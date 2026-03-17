## Why

The repository now uses OpenSpec as its canonical workflow, but the default schema does not yet encode the harness-engineering behaviors needed for iterative agent-driven development. We need lightweight change metadata, dependency handling, and task-selection conventions so agents can avoid stale assumptions, keep backlog state explicit, and find the next viable task quickly.

## What Changes

- Extend repository governance to define OpenSpec changes as the canonical backlog surface for non-archived work.
- Add durable rules for change status, assumption tracking, blocker tracking, and discovery triage during execution.
- Define artifact expectations by change type so feature, harness, validation, refactor, and spike work do not all require the same documentation weight.
- Introduce a repository-level convention for machine-readable change metadata that supports deterministic filtering and ranking.
- Add a small repository tool to list and sort candidate changes using computable fields rather than ad hoc agent judgment.

## Capabilities

### New Capabilities
- `change-backlog-triage`: Defines machine-readable change metadata, backlog states, dependency handling, and next-change selection conventions for harness-engineering work.

### Modified Capabilities
- `repository-governance`: Expand the repository workflow rules to include OpenSpec-first backlog handling, discovery triage, and disposition rules for blocked and superseded changes.

## Impact

- Affects repository governance artifacts under `openspec/project.md` and `openspec/specs/`.
- Adds change-template or repository guidance updates for future proposals.
- Adds a repository-local backlog/query tool for filtering and ranking non-archived changes.
- Influences how agents and maintainers create, continue, block, supersede, and archive OpenSpec changes.
