## Context

Archived change `record-change-state-query-mismatch` established two durable findings that remain true:

1. Repository planning currently exposes different answers depending on whether a maintainer asks for raw metadata, repository-local backlog recommendation, OpenSpec task progress, or OpenSpec artifact readiness.
2. The normal backlog question is already answered more reliably by repository facts than by hand-maintained labels such as `queued`.

The remaining gap is not just mismatch presentation. The repository still seeds and documents `status: queued` as though it were the primary backlog definition, while the actual recommendation model already prefers derived signals such as dependency resolution, superseded disposition, and task progress. That keeps agents doing unnecessary interpretation work and encourages stale metadata.

## Goals / Non-Goals

**Goals:**
- Remove `queued` as a normal repository planning status and define backlog in terms of derived `eligible` state.
- Stop requiring agents to maintain a hand-authored metadata label for ordinary "work exists and can be recommended" situations.
- Keep explicit machine-readable metadata for exception dispositions that are not recoverable from repository facts alone.
- Add durable workflow guidance that `openspec status` means artifact readiness, not change completion.

**Non-Goals:**
- Do not redesign OpenSpec CLI behavior itself.
- Do not introduce multi-branch change-state tracking in this change.
- Do not eliminate repository-owned metadata entirely.
- Do not attempt to infer whether another Git branch is actively implementing a change.

## Decisions

### Decision: Make `eligible` the primary backlog state and keep it fully derived
The backlog view should answer one operator-facing question: "Which non-archived changes are currently recommendable from repository facts?" The returned state should therefore be derived rather than hand-maintained, and the repository should use `eligible` as that primary label.

Alternative considered:
- Keep `queued` in metadata and only improve documentation. Rejected because it preserves a stale manual field for a state the repository can already derive more reliably.

### Decision: Remove normal-workflow labels such as `queued` and `active` from raw metadata
Raw metadata should keep only explicit exception dispositions that cannot be inferred reliably from tasks and dependencies alone. In this repository, the durable remaining cases are `blocked` and `superseded`. Ordinary progress should be read from task state and derived backlog tooling instead of a manual `status` label.

Alternative considered:
- Remove `queued` but keep `active` as a normal manual state. Rejected because that still asks maintainers to mirror task/workflow progress in metadata and recreates the same drift problem under a different label.

### Decision: Treat `openspec status` as archive-readiness input, not change completion
`openspec status` reports schema/artifact readiness. That signal remains useful, but repository guidance should state directly that a change is not complete until task progress and closeout expectations are also satisfied.

Alternative considered:
- Leave `openspec status` semantics implicit and rely on agents to read OpenSpec CLI behavior correctly. Rejected because the current workflow repeatedly shows that agents over-interpret the word "complete" when the durable guidance does not separate artifact readiness from change completion.

### Decision: Migrate scaffolding and guidance together with backlog tooling
Changing only the backlog script would leave new changes seeded with outdated metadata and would keep repository docs telling agents to inspect `queued`. The migration should therefore update tooling, templates, and workflow text in one pass.

Alternative considered:
- Update scripts first and leave docs for later. Rejected because partial migration would create a new temporary inconsistency while trying to remove the old one.

## Risks / Trade-offs

- [Existing active changes still carry `status: queued`] -> Treat legacy values as migration-compatible input until affected changes are updated or archived.
- [Some maintainers may still want a manual "currently doing this" flag] -> Keep task progress and Git history as the normal continuation signals rather than adding a second manual state channel.
- [Removing `queued` may surprise scripts or habits that filter raw metadata directly] -> Update repository guidance and backlog tooling together, and preserve explicit raw-metadata inspection for remaining exception dispositions.
- [Agents may still misread OpenSpec workflow outputs] -> Add durable workflow guidance that artifact completeness is not the same as change completion.

## Migration Plan

1. Update durable specs to redefine backlog around derived `eligible` state and to document artifact-readiness semantics.
2. Update repository guidance and change metadata conventions to stop advertising `queued`.
3. Update scaffolding and backlog tooling so newly created changes and recommendation queries align with the new model.
4. Preserve temporary compatibility for legacy `queued` metadata while active changes are migrated or archived.
5. Update lingering workflow wording that still tells agents to promote follow-up findings into "queued changes".

## Remaining Migration Debt

- Existing non-archived changes may still carry legacy raw `status: queued`; the new tooling treats that as compatibility input with a `legacy_meta_status` diagnostic until those changes are updated or archived.
- Archived history still contains old `queued` and `active` metadata values; this change does not rewrite archived artifacts retroactively.
- Raw metadata inspection still exposes legacy status values when they exist, because compatibility is preferable to hard failure during the transition.

## Open Questions

- Should `meta.yaml.status` remain present but optional for explicit dispositions, or should repository tooling move exception disposition into a different field name later?
- Should the backlog tool expose a derived `active-like` diagnostic for human inspection, or is task progress plus commit distance enough?
