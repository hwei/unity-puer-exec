## Context

The archived spike `improve-openspec-change-status-querying` established that raw repository planning metadata and generic OpenSpec workflow progress answer different questions. That finding still holds, but the current discussion challenges a deeper assumption: perhaps the repository should not rely so heavily on manually transitioned planning states in the first place.

Today the repository backlog model depends on explicit `meta.yaml.status` values such as `queued`, `active`, `blocked`, and `superseded`. The user wants to reduce manual state drift by deriving backlog recommendation from repository facts that already exist:

- whether a change is archived or still non-archived
- whether `blocked_by` prerequisites are resolved
- whether a dependency reference is missing or inconsistent
- how recently a change appears in Git history

At the same time, the repository already has a durable governance rule for discarded work: superseded changes should be marked `superseded` and then archived rather than silently deleted. This suggests that some manual disposition signal may still be valuable even if backlog recommendation becomes more derived.

## Goals / Non-Goals

**Goals:**
- Explore a backlog model that reduces manual status transitions and derives recommendation from repository facts.
- Preserve standard OpenSpec disposition for abandoned or replaced changes.
- Decide whether Git commit distance is a better continuation signal than wall-clock timestamps.
- Produce a concrete recommendation for a follow-up implementation change if the model looks sound.

**Non-Goals:**
- Do not implement a new backlog algorithm in this spike.
- Do not silently remove repository-owned metadata fields during exploration.
- Do not replace OpenSpec archive history with deletion-based cleanup.

## Decisions

### Decision: Treat superseded disposition as a temporary pre-archive signal
The repository should continue to support an explicit superseded signal when maintainers decide that a change is no longer the recommended path, but that signal should be temporary and archive-bound rather than a normal long-lived backlog state. This follows the existing governance requirement that replaced changes are marked superseded and archived rather than deleted, while still reducing long-lived manual state drift.

Alternative considered:
- Remove all manual disposition state and rely only on archive presence. Rejected because "no longer the recommended path" is a human decision that may need to remain visible before archive occurs.

### Decision: Explore backlog recommendation as derived eligibility plus ranking
Backlog recommendation should be framed as two questions:

1. Is this change currently eligible to be recommended?
2. If it is eligible, how strongly should it be preferred over other eligible changes?

This separates repository facts that gate recommendation from softer signals that only influence ordering.

Alternative considered:
- Continue modeling recommendation primarily as a direct filter over hand-maintained queued/active/blocked states. Rejected for this spike because that is the part most vulnerable to drift.

### Decision: Missing dependencies should be diagnostic, not resolved
If a `blocked_by` reference points to no active or archived change, the repository should treat that as inconsistent state and surface a warning rather than silently treating the dependency as resolved.

Alternative considered:
- Treat missing references as automatically resolved because no matching change exists. Rejected because typos or accidental deletions would silently turn broken metadata into false readiness.

### Decision: Git commit distance is the primary candidate continuation signal
When ranking eligible changes, the primary activity signal to evaluate should be commit distance from the most recent commit that touched the change directory, rather than only wall-clock file modification time. Commit distance better reflects how close a change is to the current development context.

Alternative considered:
- Use filesystem modified timestamps only. Rejected because timestamps are easier to drift through incidental edits and do not reflect the surrounding commit context.

### Decision: Remove queued, active, and blocked from the main recommendation model
The preferred direction is to stop using `queued`, `active`, and `blocked` as the main repository recommendation categories. Recommendation should instead derive from repository facts such as prerequisite resolution, archive state, explicit superseded disposition, and consistency diagnostics.

Alternative considered:
- Keep a hybrid state machine where queued/active/blocked remain first-class recommendation categories. Rejected because it preserves the same class of manual drift that motivated this spike.

## Recommended Model

```text
backlog recommendation
  = derived eligibility
  + derived ranking

manual disposition
  = temporary superseded-before-archive only
```

### Derived eligibility
A non-archived change is eligible for recommendation when:

- it is not explicitly superseded
- every `blocked_by` entry resolves to a known satisfied prerequisite
- no dependency reference is missing or inconsistent

Resolved prerequisite should mean one of:
- the prerequisite change is archived
- or a later agreed implementation model explicitly defines another repository-visible resolved state

Missing prerequisite should mean:
- no matching active or archived change exists
- recommendation output surfaces a warning instead of silently treating the prerequisite as resolved

### Derived ranking
Among eligible changes, recommendation order should prefer:

1. higher `priority`
2. smaller Git commit distance from the latest commit that touched the change directory
3. larger unlock count
4. better `assumption_state`
5. stronger `evidence`
6. deterministic tie-break such as change name

### Temporary superseded disposition
`superseded` remains allowed only to cover the gap between:

1. a human deciding a change is no longer the recommended path
2. the change being archived

It should not be treated as a normal long-lived backlog bucket.

## Follow-up Implementation Shape

The likely implementation-oriented follow-up should cover:

- revising `openspec/specs/change-backlog-triage/spec.md` to replace backlog-as-queued semantics with derived eligibility semantics
- updating `tools/openspec_backlog.py` to compute:
  - eligibility
  - ineligibility diagnostics
  - ranking from priority + commit distance + unlock count + remaining metadata
- deciding whether `meta.yaml.status` should shrink to:
  - `superseded` only
  - or a very small disposition field that keeps `superseded` as the only common manual value
- updating repository guidance so maintainers archive superseded changes quickly instead of leaving them in planning scans

## Risks / Trade-offs

- [Derived recommendation could become too implicit] -> Preserve explicit visibility into why a change is eligible, ineligible, or warned.
- [Git commit distance may be noisy under rebases or batching] -> Treat it as a ranking signal, not as a hard state transition.
- [Reducing manual statuses may conflict with current durable requirements] -> Keep this spike focused on recommending a spec revision path before implementation.
- [Temporary superseded could still linger indefinitely if archive hygiene is weak] -> Make the follow-up change define archive urgency and make stale superseded entries visible.

## Open Questions

- Should the follow-up remove `status` from `meta.yaml` entirely or preserve a narrow `status` field whose only meaningful non-archive value is `superseded`?
- Should backlog recommendation distinguish "eligible to start" from "eligible to continue" as separate output fields, or only as ranking rationale?
- How should non-change prerequisites outside repository state be modeled if explicit `blocked` is no longer first-class?
