## Context

The newly archived revalidation round confirmed that `unity-puer-exec` remains usable for the repository's two baseline help-only agent workflows, but both tasks still scored `recoverable` rather than `clean`. The remaining friction is not just help discoverability anymore. Both tasks still escape the intended CLI verification surface:

- Prompt A succeeded only after explicit startup recovery and then used direct host scene-file confirmation.
- Prompt B succeeded only after compile recovery, selection-state debugging, and a final fallback to direct `Editor.log` inspection.

A direct manual probe performed after that revalidation also established an important control case: a minimal workflow that writes a simple C# static method and then immediately issues a second `exec` to call that method succeeds without an explicit `wait-until-ready` between the two requests. That result suggests the current Prompt B evidence is not enough to conclude that compile recovery itself is broken as the normal CLI path; the editor-interaction shape of the task likely contributes materially to the observed fallback behavior.

That means the current problem is narrower than general usability but deeper than help wording. The repository already has contract pieces for `request_id`, `wait-for-exec`, `wait-for-log-pattern`, `wait-for-result-marker`, `log_offset`, and effective log-path handling. The design work for this change is to determine why those surfaces still do not produce a clean first-choice verification workflow for basic agent tasks.

## Goals / Non-Goals

**Goals:**
- Clarify which parts of the current verification workflow are product gaps versus agent prompt or script-authoring noise.
- Preserve a shared change for the common verification-closure problem while keeping Prompt A and Prompt B as separate acceptance tracks.
- Identify whether the main gap is contract shape, help guidance, runtime observation behavior, or some combination of those.
- Land durable OpenSpec guidance that can support a later implementation change without prematurely locking the mechanism.

**Non-Goals:**
- Do not expand the task set beyond the current basic Prompt A and Prompt B workflows.
- Do not assume the solution is only help text or only runtime changes before exploration is complete.
- Do not fold the broader project-scoped startup-reliability problem into this change unless it proves inseparable from verification closure.

## Decisions

### Decision: Keep the change centered on verification closure, not all runtime friction
The revalidation evidence surfaced both startup friction and verification friction, but this change should first focus on the shared gap: agents still leave the intended CLI-native confirmation path to verify success. Startup reliability remains important, but it does not currently explain Prompt B's fallback to direct host-log inspection by itself.

Alternative considered:
- Merge startup reliability and verification closure into one broad runtime-improvement change. Rejected because it would blur diagnosis and make it harder to decide which parts of the workflow actually need contract or surface changes.

### Decision: Use Prompt A and Prompt B as separate acceptance tracks inside one shared change
Prompt A and Prompt B experience different workflow friction, but both are still exercising the same user-facing promise: an agent should be able to confirm success through the CLI surface without host-side fallback. The change should therefore keep one shared problem statement while treating A and B as independent evidence tracks during exploration and validation.

Alternative considered:
- Split immediately into separate Prompt A and Prompt B changes. Rejected because the common verification-closure hypothesis has not been ruled out yet.

### Decision: Explore contract and workflow shape before implementation
The repository already exposes multiple observation and recovery surfaces, so the next productive step is to inspect whether the gap is missing capability, poor composition, or insufficient guidance. This change should therefore explicitly reserve early tasks for problem decomposition and option comparison before any implementation work is proposed.

Alternative considered:
- Start implementing a guessed verification helper immediately. Rejected because the current evidence still allows multiple different root causes.

### Decision: Prompt A should treat slow project-scoped startup as an accepted exec lifecycle
For the Prompt A class of workflow, the preferred product behavior is that `exec --project-path ...` becomes the clear primary path even when Unity startup or recovery is slow. If the CLI has already taken ownership of the project-scoped startup or recovery flow for the exec request, it should prefer returning a non-terminal accepted state such as `running` with a stable `request_id`, rather than a terminal-looking startup failure that pushes the caller into ad hoc diagnosis.

The returned payload should also include a default follow-up hint that is explicit enough for medium-capability agents to use directly, including a complete recommended `wait-for-exec` argv. A future quieting flag may suppress these hints for callers that want to minimize output volume, but the default behavior should bias toward agent-friendly continuity.

Alternative considered:
- Continue treating slow startup as a plain exec failure and expect the caller to switch to `wait-until-ready`. Rejected because it makes the nominal work command look terminal too early and turns a normal project-scoped exec path into a two-command recovery dance.

### Decision: Wait-for-exec continues one request lifecycle, not cross-session recovery
The Prompt A improvement should expand `wait-for-exec` to cover a broader portion of the same request lifecycle, including startup, readiness recovery, and compile-time waiting when the original request remains valid. It should not, however, imply cross-session or cross-runtime resurrection. If session replacement, runtime loss, or script-reload invalidation breaks the original request identity, `wait-for-exec` should fail explicitly rather than pretending the original request can continue across that boundary.

Alternative considered:
- Treat `wait-for-exec` as a generic recovery command that can span session replacement or post-compilation request invalidation. Rejected because it would blur the request contract and create false expectations about what `request_id` continuity means.

## Risks / Trade-offs

- [The common root-cause hypothesis may be wrong] → Keep Prompt A and Prompt B acceptance separate so a later split remains easy if the evidence diverges.
- [The change may stay abstract for too long] → Make the early tasks produce concrete problem decomposition and candidate solution comparisons, not only general discussion.
- [Verification closure may depend on startup behavior more than expected] → Reassess scope during exploration and open or link a dedicated startup-focused follow-up if needed.
