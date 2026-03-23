## Context

The Selection/menu validation scenario exposed real friction, but a later control probe showed that a simpler write-compile-call C# workflow succeeds without the same recovery path. That means the editor-interaction case is still useful, but it is not currently a clean baseline for judging the core CLI workflow in isolation.

## Goals / Non-Goals

**Goals:**
- Preserve fragile editor-interaction validation as an explicit future work item.
- Make its dependency on earlier core-workflow and log-observation clarification visible.
- Avoid losing the rationale for revisiting this scenario later.

**Non-Goals:**
- Do not re-run or redesign the editor-interaction validation immediately.
- Do not treat this scenario as the main current baseline for core workflow quality.

## Decisions

### Decision: Keep editor-interaction validation deferred
This scenario should remain available for later revalidation, but only after the repository has addressed more targeted core workflow questions first.

Alternative considered:
- Continue using the Selection/menu scenario as the main Prompt B baseline. Rejected because it currently mixes Unity Editor timing traps with broader CLI workflow evaluation.

## Risks / Trade-offs

- [Deferring the scenario may delay discovery of editor-specific weaknesses] → Keep the change visible and explicitly linked rather than dropping the scenario entirely.
