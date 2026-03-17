## Context

The previous migration established OpenSpec as the canonical workflow and specification system, but the repository still contains accepted decision prose in the working tree. Those files overlap with OpenSpec specs for governance, validation-host integration, and the formal CLI contract.

The desired end state is stricter than a compatibility layer: the working tree should stop carrying old decision files at all, and git history should remain the only legacy record.

## Goals / Non-Goals

**Goals:**
- Remove legacy decision files from the working tree entirely.
- Leave OpenSpec as the only current durable governance surface.
- Preserve the old decision texts only in git history.

**Non-Goals:**
- Rewrite the historical texts.
- Change any product or workflow requirement already captured in OpenSpec specs.

## Decisions

### Decision: Remove legacy decision files completely

Legacy decision documents will be removed from the working tree once their durable content has been migrated into OpenSpec. Git history remains sufficient for historical reconstruction.

### Decision: Keep canonical references only in OpenSpec

Repository guidance and durable requirements will point only to OpenSpec artifacts, not to compatibility stubs or copied historical prose.

## Risks / Trade-offs

- [Risk] Older external notes may reference deleted `docs/decisions/` paths. -> Mitigation: accept that break in the working tree and rely on git history when historical lookup is actually needed.
- [Risk] A contributor may still want old prose during future exploration. -> Mitigation: use git history or archived OpenSpec changes instead of keeping duplicate working-tree files.
