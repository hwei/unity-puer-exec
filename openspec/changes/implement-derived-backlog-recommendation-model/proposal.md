## Why

The spike `derive-backlog-recommendations-from-repository-state` concluded that backlog recommendation should be driven mainly by repository facts instead of hand-maintained queued/active/blocked transitions. That finding is ready to turn into a repository-local implementation: the current backlog tool should recommend work from derived eligibility and ranking, while keeping `superseded` only as a temporary pre-archive disposition.

## What Changes

- Replace the current backlog-as-queued recommendation model with a repository-derived eligibility model.
- Update backlog ranking to incorporate Git commit distance as the primary recent-activity signal.
- Surface missing `blocked_by` references as diagnostics instead of silently treating them as resolved.
- Narrow repository-owned planning state so `superseded` remains the only meaningful temporary manual disposition in normal backlog scans.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: backlog recommendation and filtering rules change from status-driven queued backlog semantics to derived eligibility, ranking, and diagnostics.
- `repository-governance`: superseded changes remain archive-bound temporary dispositions rather than long-lived planning buckets.

## Impact

- Affects `tools/openspec_backlog.py` and its tests.
- Affects repository-owned metadata handling in `tools/openspec_change_meta.py` and change templates if the metadata shape is narrowed.
- Affects durable workflow guidance in `openspec/specs/change-backlog-triage/spec.md` and `openspec/specs/repository-governance/spec.md`.
