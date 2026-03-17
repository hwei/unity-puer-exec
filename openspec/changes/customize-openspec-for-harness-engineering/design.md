## Context

The repository already uses OpenSpec for canonical governance, but the default change scaffold does not provide enough structure for harness-engineering work. The missing pieces are mostly workflow concerns rather than product concerns: explicit backlog state, dependency visibility, assumption visibility, and a fast way to identify the next viable change when the working tree is clean.

This customization needs to stay lightweight. If the metadata model becomes too heavy, agents and maintainers will stop keeping it current. The design therefore favors a small machine-readable surface for deterministic filtering and ranking, while leaving explanatory reasoning in normal OpenSpec artifacts.

## Goals / Non-Goals

**Goals:**
- Treat non-archived OpenSpec changes as the canonical backlog surface.
- Add a small machine-readable metadata file per change so tooling can filter and sort candidate work without parsing free-form prose.
- Define a small set of change states that make blocked and superseded work explicit.
- Define change-type-specific artifact expectations so harness, validation, spike, and refactor work can use lighter or heavier documentation appropriately.
- Provide a repository-local tool that deterministically ranks candidate changes from computable fields and reports why they were ordered that way.

**Non-Goals:**
- Replace OpenSpec's built-in schema or archive behavior.
- Build a fully automated planner that overrides human or agent judgment.
- Encode every planning concern as machine-readable metadata.
- Auto-invalidate dependent changes transitively when an upstream change is abandoned.

## Decisions

### Decision: Use non-archived changes as the planning surface, with queued changes as backlog

OpenSpec changes that have not yet been archived will be the repository's planning surface. Within that surface, backlog is defined narrowly as changes whose metadata status is `queued`. Other non-archived statuses remain first-class planning states, but they are not backlog: `active` means in progress, `blocked` means not currently actionable, and `superseded` means no longer the recommended path and awaiting archive. This avoids introducing a second planning system and keeps agent discovery focused on one directory tree.

Alternatives considered:
- Separate backlog document: rejected because it creates drift from actual change artifacts.
- Durable spec-only backlog: rejected because specs describe long-lived truth, not queued work.

### Decision: Add a small per-change metadata file for computable fields

Each change will gain a repository-owned metadata file, `meta.yaml`, alongside the standard OpenSpec artifacts. The file is intentionally small and stable so a local tool can parse it without reading free-form markdown.

Planned fields:
- `status`: `queued | active | blocked | superseded`
- `change_type`: `feature | harness | validation | refactor | spike`
- `priority`: `P0 | P1 | P2`
- `blocked_by`: list of change names
- `assumption_state`: `valid | needs-review | invalid`
- `evidence`: `tests | host-validation | cli-transcript | manual-check`
- `updated_at`: ISO date

Alternatives considered:
- Parse metadata from `proposal.md`: rejected because template drift would make tooling brittle.
- Extend `.openspec.yaml`: rejected because it is OpenSpec-owned schema state, not repository-specific planning metadata.

### Decision: Keep assumptions explicit but only partially machine-readable

Assumptions remain primarily explanatory content in proposal or design artifacts, while the metadata file exposes only `assumption_state` for ranking and warning purposes. This keeps the machine-readable surface small without losing the ability to signal stale assumptions.

Alternatives considered:
- Fully structured assumptions list: rejected for the first iteration because maintenance cost is high.
- No assumption signal in metadata: rejected because it would leave ranking blind to stale plans.

### Decision: Use single-direction dependency recording

Changes will record `blocked_by`, but they will not record reciprocal `unblocks` links. The local tool can derive unlock impact by counting how many non-archived changes reference a change in `blocked_by`.

Alternatives considered:
- Bidirectional dependency fields: rejected because they are easy to let drift.
- No dependency field at all: rejected because blocked work becomes invisible to tooling.

### Decision: Rank changes using deterministic rules and present reasons

The local tool will filter out non-actionable work and sort remaining changes using only computable data. The tool should not auto-start work; it should present a ranked list with reasons so a person or agent can make the final selection.

Initial ordering rules:
1. `active` before `queued`
2. `assumption_state=valid` before `needs-review`
3. `priority`: `P0` before `P1` before `P2`
4. Higher derived unlock count before lower unlock count
5. Evidence order optimized for fast closure: `tests`, `host-validation`, `cli-transcript`, `manual-check`
6. More recently updated changes before staler entries when otherwise tied

Alternatives considered:
- Subjective unlock-value field: rejected because the user wants code-computable ranking.
- Free-form agent reasoning only: rejected because it is slower and less consistent.

### Decision: Define artifact expectations by change type

The repository will define artifact weight by change type rather than forcing every change into the same documentation burden.

Expected policy:
- `feature`: proposal required, spec required, tasks required, design required when architecture changes materially
- `harness`: proposal required, tasks required, design usually required, spec required when durable contract or workflow requirements change
- `validation`: proposal required, tasks required, design optional, spec only when durable validation policy changes
- `refactor`: proposal required, tasks required, design optional unless coordination risk is high, spec only when external behavior or governance changes
- `spike`: lightweight proposal required, tasks required, design optional, spec only if the spike produces durable requirements

Alternatives considered:
- Always require proposal, design, specs, and tasks: rejected because it over-documents exploratory and validation-heavy work.
- Leave artifact weight implicit: rejected because agents need explicit guidance.

### Decision: Treat superseded changes as archiveable history

OpenSpec CLI does not provide a dedicated superseded archive path, so the repository will treat `superseded` as a repository-level status. Once a superseded change's disposition is clear, it should be archived, typically with `--skip-specs` when no durable spec update belongs in mainline specs.

Alternatives considered:
- Delete superseded changes: rejected because it loses decision history.
- Leave superseded changes unarchived indefinitely: rejected because they clutter backlog scans.

## Risks / Trade-offs

- [Metadata drift] -> Keep the field set small and add repository guidance plus validation-oriented tests for the local tool.
- [Overfitting workflow to current preferences] -> Start with minimal states and ranking rules, and evolve via later changes if real usage exposes gaps.
- [False precision in ranking] -> The tool will explain ranking inputs and remain advisory rather than authoritative.
- [Change-type ambiguity] -> Document concise type definitions and allow manual correction rather than trying to infer type automatically.

## Migration Plan

1. Add durable governance requirements and the new backlog-triage capability in OpenSpec specs.
2. Update repository context and agent guidance to reference the metadata file and change-state model.
3. Add or adapt a lightweight template for `meta.yaml` in new changes.
4. Implement the repository-local ranking tool and validate it against sample or real changes.
5. Adopt the metadata file incrementally for active and queued changes rather than rewriting archived history.

## Open Questions

- Whether the metadata template should be injected automatically by a repository helper or maintained manually after `openspec new change`.
- Whether the tool should warn on stale `updated_at` thresholds or only use the field for tie-breaking.
