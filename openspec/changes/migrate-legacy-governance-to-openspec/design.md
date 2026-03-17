## Context

This repository developed a custom governance stack before adopting OpenSpec. The old stack split responsibility across `docs/index.md`, `docs/workflow.md`, `docs/planning.md`, `docs/workflow-closeout.md`, `docs/status.md`, `docs/roadmap.md`, and several `docs/decisions/*.md` files. That model works, but it is not change-centric and does not map cleanly onto OpenSpec's `project.md` plus `specs/` plus `changes/` structure.

The migration needs to preserve durable rules without preserving the old task-tree workflow itself. The repository also has product-facing requirements already captured in accepted decisions, especially the validation-host operating model and the formal CLI contract, so the new OpenSpec baseline must keep those requirements testable instead of collapsing them into prose guidance.

## Goals / Non-Goals

**Goals:**
- Make OpenSpec the canonical governance and specification entry point for the repository.
- Separate repository-wide context and collaboration rules from durable testable requirements.
- Preserve current durable product and harness requirements while retiring the old docs workflow as the authority.
- Keep the migration reviewable by recording it as an OpenSpec change with proposal, design, specs, and tasks.

**Non-Goals:**
- Recreate the legacy global roadmap tree inside OpenSpec.
- Change the implemented CLI behavior or Unity package behavior as part of this migration.
- Archive the migration change automatically without user review.

## Decisions

### Decision: Split legacy docs into `project.md` plus three long-lived capabilities

`openspec/project.md` will carry repository identity, environment setup, collaboration expectations, and OpenSpec working agreements. Long-lived requirements will be split into exactly three capabilities:

- `repository-governance`
- `validation-host-integration`
- `formal-cli-contract`

This is the smallest split that preserves clear ownership boundaries between process rules, harness/host rules, and product CLI contract rules.

Alternative considered: Port everything into one large repository spec. Rejected because it would mix agent workflow rules with product CLI behavior and make later changes harder to review.

### Decision: Treat legacy `docs/` as transitional redirects, not as parallel truth

The migration will not leave full duplicated governance content in `docs/`. Instead, the top-level legacy workflow documents will be reduced to notices pointing to OpenSpec. This keeps existing file paths discoverable while making the canonical source unambiguous.

Alternative considered: Delete the legacy docs immediately. Rejected because lightweight redirects are safer for current collaborators and preserve path continuity during the transition.

### Decision: Carry accepted decision content into specs, not into project guidance

The accepted decisions in `docs/decisions/0001`, `0003`, `0005`, and `0007` already describe durable contract behavior. They will be normalized into OpenSpec requirements with scenarios. Historical decision files may remain temporarily, but they will no longer be canonical.

Alternative considered: Keep accepted decisions as the long-lived truth and only add OpenSpec wrappers. Rejected because that would preserve the dual-authority problem the migration is meant to remove.

## Risks / Trade-offs

- [Risk] Some legacy docs paths may still be referenced informally by humans or scripts. -> Mitigation: keep redirect stubs instead of hard deletion.
- [Risk] The migration may accidentally preserve the old roadmap-tree mindset inside OpenSpec. -> Mitigation: explicitly avoid porting `docs/roadmap.md` as a long-lived spec or backlog artifact.
- [Risk] `0006-minimal-host-validation-proof` mixes evidence and requirements. -> Mitigation: migrate only normative expectations into the new validation-host spec.
- [Risk] The new CLI spec is substantial and could drift from code if under-specified. -> Mitigation: preserve the formal contract structure and point future work back to tests and CLI help.

## Migration Plan

1. Create a migration change that records the OpenSpec adoption work.
2. Author change-local specs for governance, validation-host integration, and formal CLI contract.
3. Implement the new long-lived OpenSpec baseline in `openspec/project.md`, `openspec/specs/`, and `openspec/config.yaml`.
4. Convert legacy governance docs into redirect notices so OpenSpec becomes the single entry path.
5. Validate OpenSpec status and repository structure, then leave the change ready for archive.

## Open Questions

- Whether the historical `docs/decisions/` files should later be archived into a dedicated legacy folder or kept as non-canonical history.
