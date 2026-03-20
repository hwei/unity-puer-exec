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

### Decision: Detect blockers from the host side on Windows first
The first implementation should detect targeted modal blockers from the host-side CLI/session layer on Windows instead of trying to query Unity for an active modal-dialog state.

Observed basis:
- The targeted save-scene blockers still allow health probes to report `ready`, so readiness state is not a reliable primary detector.
- The Windows host can enumerate Unity-owned modal dialog windows and distinguish the observed `Scene(s) Have Been Modified` and `Save Scene` dialogs by title.

Alternative considered:
- Require a Unity-side public API or event for active dialog inspection. Rejected because the public surface used in this repository does not currently expose a reliable active-modal query for these dialogs.

### Decision: Scope blocker reporting to exec follow-up and explicit blocker queries
The first implementation should report modal blockers through `exec`, `wait-for-exec`, and an explicit blocker-query command. `wait-until-ready` should remain unchanged for now.

Rationale:
- The reproduced save-scene blockers occur after exec-side work has already started.
- `wait-until-ready` can still report normal readiness while an exec-triggered modal dialog blocks the Editor main thread.
- Contributors can use the explicit blocker-query command after timeout-like symptoms instead of overloading readiness semantics prematurely.

Alternative considered:
- Make `wait-until-ready` a first-class detector in the initial implementation. Rejected because current evidence does not show that readiness probes can distinguish these blockers reliably.

### Decision: Keep blocker payload minimal
The first branchable blocker payload should expose only `type` and `scope`.

Rationale:
- The caller mainly needs a stable machine-branchable state and blocker class.
- Recovery ownership remains with the caller or operator, so extra metadata is not required for the first contract.

## Risks / Trade-offs

- [Modal detection may be heuristic and platform-specific] → Start with a narrow supported scenario and report diagnostics clearly when confidence is limited.
- [Explicit blocker reporting may require additional observation hooks] → Keep the first change focused on detectable machine outcomes, not perfect UI introspection.
- [Broader dialog coverage can sprawl] → Treat non-target dialogs as future follow-up only after the first blocker path is stable.

## Current Limits

- The first implementation is Windows-only because it relies on Win32 window enumeration against the Unity Editor process.
- The first implementation recognizes only the observed save-scene blockers:
  - `save_modified_scenes_prompt` for the `Scene(s) Have Been Modified` dialog
  - `save_scene_dialog` for the `Save Scene` file-save dialog
- Other Unity-native dialogs remain unsupported until they are reproduced and given stable detector rules.
