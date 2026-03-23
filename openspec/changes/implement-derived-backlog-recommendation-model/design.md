## Context

The upstream spike `derive-backlog-recommendations-from-repository-state` established four findings that remain true:

- backlog recommendation should be split into derived eligibility and derived ranking
- missing `blocked_by` references should be treated as diagnostics, not as resolved prerequisites
- Git commit distance is a better continuation signal than plain timestamp recency
- `superseded` should survive only as a temporary pre-archive disposition

This implementation change takes those findings and applies them to the repository's actual backlog tooling and durable rules. The main design challenge is deciding how far to narrow `meta.yaml.status` without leaving the repository in an awkward mixed model.

## Goals / Non-Goals

**Goals:**
- Implement a derived backlog recommendation algorithm in `tools/openspec_backlog.py`.
- Update durable specs so backlog semantics no longer depend on queued/active/blocked categories.
- Preserve a clear explicit path for superseded changes before archive.
- Keep output machine-usable by exposing eligibility, ranking reasons, and diagnostics.

**Non-Goals:**
- Do not change generic OpenSpec CLI behavior.
- Do not introduce a second repository-local planner beyond the backlog tooling.
- Do not delete historical archived changes or hide archive records.

## Decisions

### Decision: Preserve `status` short-term but narrow its meaning
This implementation should keep a `status` field in `meta.yaml` for file-format continuity, but change repository semantics so only `superseded` remains a meaningful temporary manual disposition in normal planning behavior. Existing values such as `queued`, `active`, and `blocked` should stop driving backlog recommendation directly.

Alternative considered:
- Remove `status` from `meta.yaml` immediately. Rejected for this implementation because it would create a larger metadata migration than needed for the first derived-model rollout.

### Decision: Backlog output exposes eligibility and diagnostics explicitly
`tools/openspec_backlog.py` should report whether each non-archived change is eligible, and if not, why not. Missing dependencies, explicit superseded disposition, unresolved prerequisites, and invalid assumption state should appear as machine-readable reasons.

Alternative considered:
- Keep the current list output shape and only change ordering internally. Rejected because the whole point of this change is to make recommendation reasoning visible.

### Decision: Git commit distance becomes the primary activity ordering signal
The backlog tool should inspect Git history to find how many commits ago each change directory was last touched. That value should be used ahead of timestamp-only recency when ranking otherwise eligible changes.

Alternative considered:
- Keep using only `updated_at` from metadata. Rejected because it is still a manual or file-level signal and does not reflect repository history context.

Validation note:
- A newly created or not-yet-committed change directory can legitimately report unknown Git distance. In that case the backlog tool should surface `git_commit_distance = null` or equivalent human-readable output and fall back to the remaining ranking signals.

### Decision: Missing dependencies are ineligible with diagnostics
If a `blocked_by` reference points to no active or archived change, the change should be treated as not currently recommendable and the output should carry a diagnostic reason such as missing dependency reference.

Alternative considered:
- Show a warning but still allow recommendation. Rejected because a missing dependency reference is more likely a repository inconsistency than a sign of readiness.

### Decision: Replace old `--status` semantics instead of preserving compatibility
The backlog tool should not preserve the old meaning where `--status queued` was effectively the backlog definition. `--status` should move to derived recommendation-oriented values, and raw metadata inspection should use more explicit filters if still needed.

Alternative considered:
- Preserve `--status` as a raw metadata filter for compatibility. Rejected because that keeps the old status-first mental model alive even after the repository adopts derived recommendation semantics.

## Risks / Trade-offs

- [Compatibility drift between old metadata semantics and new backlog semantics] -> Keep the first rollout backward-compatible at the file-format level, but allow the backlog CLI surface to break in favor of clearer derived semantics.
- [Git history queries may be slower than pure metadata ranking] -> Restrict queries to change directories and cache or batch where possible.
- [Superseded entries may still linger] -> Treat them as explicit non-eligible entries and update governance guidance to archive them promptly.
- [Users may expect `--status queued` filtering to keep working exactly as before] -> Decide explicitly whether status filtering remains raw-metadata inspection or is replaced by eligibility filtering.

## Open Questions

- What exact machine-readable keys should the backlog JSON output expose for diagnostics and Git-distance ranking?
