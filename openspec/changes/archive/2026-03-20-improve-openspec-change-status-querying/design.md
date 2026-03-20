## Context

The repository intentionally keeps `meta.yaml` narrow and machine-readable. Earlier governance work established that change state lives in explicit finite metadata values and that dependency references such as `blocked_by` are planning inputs, not narrative background.

Current repository state exposes a simpler and more direct mismatch. `improve-openspec-change-status-querying/meta.yaml` records `status: queued`, `tools/openspec_backlog.py` reflects that raw metadata in backlog views, and `openspec list --json` reports the same non-archived change as `status: "in-progress"` because the OpenSpec CLI treats an active directory with unfinished tasks as work in progress. This means contributors can receive different answers depending on whether they ask for repository backlog state or generic OpenSpec workflow state.

This change is a spike because the problem statement is clearer than the solution. We know the repository needs a more trustworthy query surface, but we have not yet decided whether the fix belongs in backlog tooling, OpenSpec query wrappers, metadata hygiene automation, or a narrower diagnostic path.

## Goals / Non-Goals

**Goals:**
- Define the observable problem in repository-owned artifacts so future work is not driven by memory.
- Establish what operators and agents need from change-query output when raw metadata and OpenSpec workflow state diverge.
- Preserve the existing principle that `meta.yaml` remains lightweight machine-readable metadata.
- Leave room for further exploration before choosing an implementation path.

**Non-Goals:**
- Do not replace `meta.yaml` with a richer narrative status document.
- Do not commit this change to one specific derivation algorithm or query command yet.
- Do not fold this problem into unrelated CLI product help work.

## Decisions

### Decision: Treat this as a query-surface problem first
The immediate issue is not that metadata exists; it is that contributors need a trustworthy read path when metadata, dependency resolution, and repository state interact awkwardly.

Alternative considered:
- Treat this only as metadata hygiene and require humans to update `meta.yaml` faster. Rejected because query tooling still needs a principled behavior when the repository is in an intermediate or abnormal state.

### Decision: Keep `meta.yaml` narrow
The repository should continue to use `meta.yaml` for explicit planning metadata rather than expanding it to carry resolved dependency narratives or derived status histories.

Alternative considered:
- Add richer derived-state fields directly to `meta.yaml`. Rejected for now because that risks duplicating query output and makes the metadata contract less stable before the real problem is explored.

### Decision: Mark the change as exploration-first
This work should stay in a spike shape until we answer where derivation belongs, what query surfaces must agree, and how raw versus interpreted state should be displayed.

Alternative considered:
- Treat this as an implementation-ready tooling fix immediately. Rejected because the user explicitly wants the problem recorded without prematurely locking the solution.

### Decision: Keep backlog tooling raw and add interpretation elsewhere
The repository backlog definition already says backlog means `meta.yaml status = queued`. That surface should stay raw and deterministic rather than silently reclassifying queued changes as active or in-progress.

Alternative considered:
- Teach `tools/openspec_backlog.py` to derive an interpreted status from OpenSpec workflow signals. Rejected because that would blur the repository's durable backlog contract and make the backlog surface less predictable.

### Decision: Preferred follow-up is a repository-local diagnostic query surface
The most plausible follow-up is a repository-owned change-state diagnostic or wrapper that reports both raw metadata state and interpreted OpenSpec workflow state side by side, with an explicit mismatch signal when they diverge.

Alternative considered:
- Rely only on metadata hygiene automation so humans update `meta.yaml` faster. Rejected because the tooling still needs a principled behavior when a repository is in a temporary mismatch state.
- Treat `openspec list` as the sole operator-facing answer. Rejected because repository backlog policy explicitly depends on raw metadata and because `openspec list` does not expose that repository-specific contract.

## Scope Comparison

### In scope query surfaces
- `meta.yaml` as the raw planning source of truth for repository backlog state
- `python tools/openspec_backlog.py ...` as the repository-local raw metadata and ranking surface
- `openspec list --json` as the generic OpenSpec workflow surface that contributors already use

### Out of scope query surfaces
- `openspec status --change ... --json`, because it reports schema/artifact readiness rather than operator-facing change state
- manual prose in change artifacts, because this spike is about machine-usable query behavior

## Candidate Behavior Comparison

### Candidate A: Keep using backlog tooling and ignore `openspec list`
- Strength: no implementation work
- Weakness: contributors still encounter `openspec list` and receive conflicting status without explanation

### Candidate B: Make backlog tooling derive interpreted state
- Strength: one repository-local command could answer more questions
- Weakness: backlog tooling would stop being a clean raw metadata view and could violate the durable "backlog means queued" contract

### Candidate C: Add a separate repository-local change-state diagnostic wrapper
- Strength: preserves raw backlog semantics while making mismatches explicit and inspectable
- Weakness: introduces another query entry point that maintainers need to learn

### Candidate D: Automate metadata hygiene only
- Strength: keeps query tooling simple
- Weakness: does not address temporary mismatch states or explain why different tools disagree

Chosen direction: Candidate C.

## Risks / Trade-offs

- [A vague spike can drift without producing actionable guidance] -> Keep the tasks focused on reproducing inconsistencies, evaluating candidate query behaviors, and deciding where the responsibility should live.
- [Query tooling may over-interpret state and hide raw metadata mistakes] -> Any future solution should preserve access to raw metadata alongside interpreted state.
- [A new wrapper could duplicate too much of `openspec list`] -> Keep the follow-up narrow: report repository metadata state, OpenSpec workflow state, and mismatch diagnostics rather than recreating the full OpenSpec CLI.
- [Solving only the current symptom may miss broader repository-state inconsistencies] -> Keep the mismatch signal generic enough to handle stale placeholders, resolved blockers, and future raw/interpreted state divergence.

## Open Questions

- Should the follow-up diagnostic wrapper consume `openspec list --json`, `openspec status`, or a narrower repository-local rule set for interpreted workflow state?
- When raw metadata and interpreted state differ, should the wrapper expose a single mismatch flag or a more specific reason taxonomy?
- Should the wrapper eventually support machine-readable repair hints, or should it remain read-only?
