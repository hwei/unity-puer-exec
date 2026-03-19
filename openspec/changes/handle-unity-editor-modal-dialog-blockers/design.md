## Context

The recent help-only validation exposed a practical blocker: a Unity-native save-scene modal dialog interrupted CLI-driven work and required manual dismissal. This is not just a validation artifact. Any project-scoped automation that dirties scenes or triggers scene transitions can encounter the same editor-native modal flow.

This belongs in durable specs because the important requirement is not the exact implementation trick, but the machine-facing behavior: callers should not have to infer from a generic timeout that a modal dialog is blocking the editor.

## Goals / Non-Goals

**Goals:**
- Define a machine-usable outcome for project-scoped workflows that are blocked by Unity-native modal dialogs.
- Ensure real-host validation can reproduce and recognize at least one modal blocker scenario.
- Prefer explicit blocker reporting or diagnostics over silent hanging behavior.

**Non-Goals:**
- Do not promise full general-purpose UI automation for every Unity dialog.
- Do not attempt to solve every editor-native blocking condition in one pass.
- Do not expand this change into unrelated long-tail exception handling.

## Decisions

### Decision: Treat modal dialogs as product-visible blockers
If a project-scoped workflow becomes blocked by a Unity-native modal dialog, the CLI should surface that state explicitly instead of collapsing it into a generic readiness or timeout failure.

Alternative considered:
- Leave modal blockers as an operator concern. Rejected because it makes the product hard to automate and obscures the real failure mode.

### Decision: Validate with one reproducible modal scenario first
The first implementation should target a reproducible blocker such as an unsaved-scene save prompt, then generalize later if the approach proves useful.

Alternative considered:
- Attempt to inventory every possible Unity modal dialog up front. Rejected because it broadens scope before the basic contract is proven.

### Decision: Separate validation design fixes from product fixes
Validation tasks should still avoid unnecessary modal triggers when possible, but the product should also grow a blocker-reporting story for unavoidable modal cases.

Alternative considered:
- Fix validation prompts only. Rejected because real users and agents can still trigger native modal dialogs in normal operation.

## Risks / Trade-offs

- [Modal detection may be heuristic and platform-specific] → Start with a narrow supported scenario and report diagnostics clearly when confidence is limited.
- [Explicit blocker reporting may require additional observation hooks] → Keep the first change focused on detectable machine outcomes, not perfect UI introspection.
- [Broader dialog coverage can sprawl] → Treat non-target dialogs as future follow-up only after the first blocker path is stable.
