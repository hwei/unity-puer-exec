## Why

Archived change `record-change-state-query-mismatch` confirmed that the repository still mixes multiple change-state questions: raw `meta.yaml` planning metadata, repository-local backlog recommendation, OpenSpec task progress, and OpenSpec artifact readiness. Keeping `status: queued` as a manually maintained planning label makes that mismatch easier to trigger without adding durable value, because the repository already derives recommendable backlog state from tasks, blockers, and archive facts.

## What Changes

- Remove `queued` as a repository planning concept and replace it with derived `eligible` backlog state.
- Stop treating `meta.yaml.status` as the place to declare normal backlog or in-progress work by hand.
- Clarify that `openspec status` reports artifact readiness only and does not by itself mean a change is complete.
- Update repository-local backlog tooling, change scaffolding, and workflow guidance to match the derived-state model.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: redefine normal backlog recommendation around derived `eligible` state instead of raw `queued` metadata, and narrow raw metadata status usage to explicit exception dispositions.
- `repository-governance`: make workflow guidance distinguish artifact readiness from change completion so agents do not over-trust `openspec status`.
- `apply-closeout-review`: replace lingering “queued change” follow-up language with neutral follow-up-change wording that matches the derived backlog model.

## Impact

- Affects `tools/openspec_backlog.py`, `tools/new_openspec_change.py`, and repository metadata helpers/templates.
- Affects repository workflow guidance in `AGENTS.md` and `openspec/project.md`.
- Affects durable OpenSpec governance requirements for change metadata, backlog recommendation, apply closeout promotion language, and archive readiness interpretation.
- Does not change product CLI runtime behavior.
