## Context

Runtime guidance is currently driven by a static matrix keyed by `(command, status)`. That design keeps follow-up guidance predictable and avoids coupling status explanations to arbitrary response payload fields.

The `unity_compile_error` response already carries structured compile diagnostics through `compile_errors_total`, `compile_warnings_total`, and `compile_messages`. Requiring the human-readable `situation` string to duplicate those counts adds payload-aware rendering pressure without improving the machine contract.

## Goals / Non-Goals

**Goals:**

- Keep runtime guidance compatible with the static guidance-matrix model.
- Preserve useful compile-error guidance for agents and humans.
- Keep structured count fields as the authoritative machine-readable detail.

**Non-Goals:**

- Change CLI runtime behavior.
- Change the `unity_compile_error` response schema.
- Add dynamic situation rendering.

## Decisions

- Relax the spec rather than changing implementation.
  - Rationale: `compile_errors_total` and `compile_warnings_total` already provide exact counts. The situation text only needs to explain where to look and what to do next.
  - Alternative considered: make `build_situation` payload-aware. That would add a second guidance rendering model for little practical benefit.

## Risks / Trade-offs

- Risk: Human readers may prefer seeing counts directly in prose.
  - Mitigation: The situation still points to the structured fields, and those fields remain in the same response.

- Risk: Future specs may accidentally reintroduce payload-aware guidance requirements.
  - Mitigation: This change reinforces the existing static guidance-matrix contract.
