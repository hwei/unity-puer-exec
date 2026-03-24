## Context

The repository has already moved away from treating `meta.yaml.status` as the sole planning answer. Backlog tooling now exposes derived states such as `eligible`, `blocked`, `inconsistent`, and `superseded`, while durable specs already say query tooling should preserve raw metadata access and also surface interpreted operator-facing state.

The current observed mismatch is narrower and more concrete: a non-archived change can still carry `status: queued` in `meta.yaml`, repository-local tooling can still expose that raw metadata view, and `openspec list --json` can simultaneously describe the same change as workflow `in-progress` because OpenSpec interprets active unfinished work differently. That is not necessarily a bug in either surface, but it is still a planning hazard when contributors are not told which question each surface answers.

This change exists to record that concrete failure mode and keep future work anchored in an explicit problem statement instead of a vague feeling that state handling is confusing.

## Goals / Non-Goals

**Goals:**
- Record the specific mismatch between raw metadata, repository-local planning views, and generic OpenSpec workflow state.
- Clarify that different query surfaces can answer different questions without one silently replacing the others.
- Recommend a likely follow-up direction that makes mismatches explicit to operators.

**Non-Goals:**
- Do not implement a new repository query wrapper yet.
- Do not redesign backlog recommendation rules in this change.
- Do not expand `meta.yaml` into a narrative or derived-status document.

## Decisions

### Decision: Treat the problem as missing mismatch presentation, not as immediate metadata corruption
The observed disagreement does not prove one source is wrong. It proves the repository still lacks a sufficiently explicit operator-facing presentation when raw metadata and workflow interpretation answer different questions.

Alternative considered:
- Treat every mismatch as metadata hygiene failure. Rejected because even well-maintained metadata can still differ from a generic workflow tool's interpretation rules.

### Decision: Anchor this change in the existing `change-backlog-triage` capability
The durable requirement already says query tooling must distinguish raw metadata from interpreted state. This follow-up should sharpen that capability with a concrete scenario instead of creating a second overlapping governance capability.

Alternative considered:
- Create a new governance capability just for change-state diagnostics. Rejected because the problem already belongs to change-query behavior.

### Decision: Preferred follow-up is a repository-local diagnostic surface
The most plausible next implementation step is a repository-local query or wrapper that reports raw metadata state, repository-derived planning state, and generic OpenSpec workflow state together, with an explicit mismatch signal.

Alternative considered:
- Rely only on contributor education. Rejected because the mismatch will keep recurring if tooling output still requires humans to infer intent manually.
- Change backlog tooling to hide raw metadata. Rejected because raw metadata inspection remains useful and is already part of the durable contract.

## Risks / Trade-offs

- [This change could restate requirements the repository already has] -> Keep the scope tied to the concrete mismatch that was reproduced during exploration.
- [A future wrapper could duplicate too much of OpenSpec CLI output] -> Keep the likely follow-up narrow and diagnostic rather than reimplementing general OpenSpec workflow reporting.
- [Contributors may still over-trust one surface] -> Future query output should label each state as raw metadata, repository-derived, or generic workflow state.

## Open Questions

- Should the future diagnostic surface call `openspec list --json` directly, or compute a narrower workflow interpretation from repository facts?
- Should mismatch reporting be read-only, or should it eventually suggest repair actions for stale metadata and archive hygiene?
- Should repository guidance standardize one default operator-facing query command, or continue supporting multiple surfaces with clearer labeling?
