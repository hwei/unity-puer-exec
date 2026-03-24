## Context

The Selection/menu validation scenario exposed real friction, but a later control probe showed that a simpler write-compile-call C# workflow succeeds without the same recovery path. That means the editor-interaction case is still useful, but it is not currently a clean baseline for judging the core CLI workflow in isolation.

A new repository-side product probe on 2026-03-24 further narrowed the question. The current CLI completed the Prompt B style workflow through a CLI-native path: write the editor script, wait through compile recovery, invoke the menu command, and verify the emitted GUID through `wait-for-log-pattern` started from the returned `log_offset`. The remaining friction now looks more like script-authoring and editor-interaction ergonomics than an outright absence of a viable CLI verification path.

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

### Decision: Reuse Prompt B wording for historical comparison
Future reruns of this deferred track should keep the archived Prompt B wording unchanged when the goal is comparison against earlier evidence. If the repository later wants a narrower or cleaner editor-interaction task, that variant should be introduced as a new named prompt instead of rewriting Prompt B in place.

### Dependency checkpoints before the next formal rerun
Before this deferred editor-interaction track becomes an authoritative rerun target again, the repository should confirm all of the following:

- Prompt A and Standard Prompt C have already answered the shared verification-closure question well enough that this harder workflow is no longer standing in as the main baseline.
- The ordinary log-observation guidance still supports `exec` plus `wait-for-log-pattern` with checkpoint capture, so a future Prompt B rerun is not dominated by a known log-workflow guidance gap.
- The rerun protocol defines a deterministic selected asset, cleanup expectations, and the expected treatment of compile recovery so reviewers can isolate editor-interaction behavior from harness ambiguity.

## Risks / Trade-offs

- [Deferring the scenario may delay discovery of editor-specific weaknesses] → Keep the change visible and explicitly linked rather than dropping the scenario entirely.
- [The latest probe may tempt the repository to promote Prompt B back into the main baseline] → Resist that move. The probe shows the workflow is viable, not that it is the right primary diagnostic target for shared verification-closure work.
