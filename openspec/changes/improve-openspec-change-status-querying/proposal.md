## Why

The current OpenSpec planning surface can show contradictory signals about a change's state. In the current repository, `improve-openspec-change-status-querying` itself still declares `status: queued` in `meta.yaml`, while `python tools/openspec_backlog.py list --status queued` continues to present it as backlog work and `openspec list --json` reports the same active directory as `status: "in-progress"`.

This gap is small but costly: agents and maintainers can lose time deciding whether to trust raw metadata, OpenSpec workflow output, or surrounding prose. We need a follow-up change that defines the problem clearly and explores how repository query tooling should present raw versus interpreted planning state without turning `meta.yaml` into a second narrative artifact.

## What Changes

- Clarify the repository requirement for OpenSpec change-query output when raw metadata and dependency context no longer tell the same story cleanly.
- Define the expected operator-facing behavior for querying change state so stale placeholders, OpenSpec workflow status, or inconsistent metadata do not silently mislead contributors.
- Capture this as an exploration-first workflow change and decide whether the next implementation step belongs in backlog tooling, a separate diagnostic wrapper, or metadata hygiene automation.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: change-query tooling should expose trustworthy interpreted planning state when raw metadata alone is no longer sufficient for operator decisions.

## Impact

- Affects repository-local OpenSpec planning and query tooling.
- Affects maintainer and agent interpretation of non-archived change state.
- Likely affects `tools/openspec_backlog.py`, repository-local wrappers around `openspec list`, and any repository guidance that currently assumes one surface alone is enough for state interpretation.
