## Context

OpenSpec now owns repository context, durable requirements, and active change planning. The remaining `docs/` files exist only as redirect stubs and no longer provide unique value.

The user is the only current collaborator and explicitly prefers a single OpenSpec-first surface over backward compatibility for deleted paths.

## Goals / Non-Goals

**Goals:**
- Remove `docs/` entirely from the working tree.
- Leave OpenSpec as the only current governance and spec entry path.
- Avoid lingering wording that suggests legacy redirect files still exist.

**Non-Goals:**
- Recreate any `docs/` content elsewhere.
- Preserve deleted path compatibility in the working tree.

## Decisions

### Decision: Delete the entire `docs/` tree

The repository will no longer carry legacy workflow redirect files. Git history and archived OpenSpec changes remain enough for historical lookup.

### Decision: Update canonical guidance instead of leaving tombstones

Repository guidance in `AGENTS.md`, `ReadMe.md`, `openspec/project.md`, and `openspec/specs/repository-governance/spec.md` will describe OpenSpec directly instead of discussing deleted legacy docs.

## Risks / Trade-offs

- [Risk] Older notes may reference deleted `docs/...` paths. -> Mitigation: accept the break and rely on git history when historical lookup is needed.
- [Risk] A future collaborator may expect top-level prose docs. -> Mitigation: keep `ReadMe.md` and OpenSpec entry points concise and explicit.
