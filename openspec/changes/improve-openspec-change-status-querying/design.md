## Context

The repository intentionally keeps `meta.yaml` narrow and machine-readable. Earlier governance work established that change state lives in explicit finite metadata values and that dependency references such as `blocked_by` are planning inputs, not narrative background.

Recent exploration exposed a separate gap: query output can still be misleading when repository state is abnormal or when metadata has not yet been updated to reflect a resolved prerequisite. In the current tree, `improve-cli-help-for-agent-efficiency` still records `status: queued` and `blocked_by: capture-agent-cli-validation-transcripts`, even though the prerequisite change is already archived and the current discussion has effectively moved the work into active consideration.

This change is a spike because the problem statement is clearer than the solution. We know the repository needs a more trustworthy query surface, but we have not yet decided whether the fix belongs in backlog tooling, OpenSpec query wrappers, metadata hygiene automation, or a narrower diagnostic path.

## Goals / Non-Goals

**Goals:**
- Define the observable problem in repository-owned artifacts so future work is not driven by memory.
- Establish what operators and agents need from change-query output when raw metadata and effective planning state diverge.
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

## Risks / Trade-offs

- [A vague spike can drift without producing actionable guidance] -> Keep the tasks focused on reproducing inconsistencies, evaluating candidate query behaviors, and deciding where the responsibility should live.
- [Query tooling may over-interpret state and hide raw metadata mistakes] -> Any future solution should preserve access to raw metadata alongside interpreted state.
- [Solving only the current symptom may miss broader repository-state inconsistencies] -> Explore placeholder directories, resolved blockers, and stale metadata together instead of optimizing for a single example.

## Open Questions

- Which query surfaces need to agree: `openspec list`, `tools/openspec_backlog.py`, a new wrapper, or all of them?
- When raw metadata and interpreted state differ, should tools show both values or only the interpreted answer with diagnostics?
- Should prerequisite resolution across archived changes change the displayed state automatically, or only influence ranking and warnings?
- How should abnormal repository state such as stale active-directory placeholders be represented in query output?
