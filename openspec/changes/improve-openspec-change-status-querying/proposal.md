## Why

The current OpenSpec planning surface can show contradictory signals about a change's state. In the current repository, `improve-cli-help-for-agent-efficiency` still declares `status: queued` and a historical `blocked_by` entry in `meta.yaml`, while the operator-facing query path already presents it as active work after the prerequisite evidence landed.

This gap is small but costly: agents and maintainers can lose time deciding whether to trust raw metadata, query output, or surrounding prose. We need a follow-up change that defines the problem clearly and explores how query tooling should present raw versus interpreted planning state without turning `meta.yaml` into a second narrative artifact.

## What Changes

- Clarify the repository requirement for OpenSpec change-query output when raw metadata and dependency context no longer tell the same story cleanly.
- Define the expected operator-facing behavior for querying change state so stale placeholders, resolved prerequisites, or inconsistent metadata do not silently mislead contributors.
- Capture this as an exploration-first workflow change without committing yet to a specific derivation algorithm or tool boundary.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: change-query tooling should expose trustworthy interpreted planning state when raw metadata alone is no longer sufficient for operator decisions.

## Impact

- Affects repository-local OpenSpec planning and query tooling.
- Affects maintainer and agent interpretation of non-archived change state.
- Likely touches `tools/openspec_backlog.py`, related OpenSpec query habits, and any repository guidance that currently assumes raw metadata is always enough for state interpretation.
