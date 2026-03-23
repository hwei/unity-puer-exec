## Context

Recent agent-validation results narrowed one recurring source of friction: agents can often complete the target workflow, but they first spend time inferring how JavaScript is supposed to talk to Unity and C# inside `exec`. The current help surface hints at the bridge shape through examples like `puer.loadType(...)`, yet it does not clearly label that bridge model as PuerTS-style usage or point callers toward a concise bridge-oriented explanation.

This matters for at least two current tracks:

- Prompt A still includes bridge-shape probing before the scene-editing script converges.
- Standard Prompt C is cleaner than the old menu-and-selection workflow, but it still depends on the agent discovering how to call a C# type from JavaScript.

At the same time, this change should stay separate from other active product questions:

- compile refresh / compile recovery ergonomics belong in `improve-agent-verification-closure`
- log-oriented waiting guidance belongs in `improve-agent-log-observation-guidance`
- fragile Selection / menu timing belongs in `revalidate-editor-interaction-workflows`

## Goals / Non-Goals

**Goals:**
- Clarify the specific bridge-discoverability gaps exposed by Prompt A and Standard Prompt C.
- Decide what minimum bridge guidance should be directly discoverable from CLI help.
- Evaluate whether the help surface should explicitly name PuerTS, show a concise bridge mental model, or link to an official reference.
- Produce durable guidance that can support a later implementation change without prematurely locking the exact wording.

**Non-Goals:**
- Do not redesign compile recovery or add a refresh-oriented runtime command in this change.
- Do not treat this change as a replacement for task-specific skills or user-authored scripts.
- Do not assume a dedicated bridge command is needed before help and example improvements are explored.

## Decisions

### Decision: Treat bridge discoverability as a separate product question
The observed bridge probing is now recurring enough that it should be tracked independently rather than left as incidental noise inside Prompt A or Standard Prompt C. This keeps the main verification-closure change focused on runtime and workflow behavior while allowing bridge guidance to be evaluated on its own merits.

Alternative considered:
- Leave bridge probing as a generic validation annoyance inside existing changes. Rejected because it is now influencing multiple baseline workflows and deserves explicit product treatment.

### Decision: Explore guidance improvements before committing to a new command or API surface
The current evidence does not yet show that a new runtime command is needed. The first layer to inspect is help and example guidance: naming the bridge model, surfacing the expected `puer.loadType(...)` style more directly, and deciding whether an official PuerTS reference link should be present.

Alternative considered:
- Assume bridge confusion requires a new CLI command. Rejected because the current friction may be addressable with clearer guidance rather than a larger product surface.

### Decision: Explicitly consider an official PuerTS reference link
An official reference link could help agents that already recognize the ecosystem pattern and want to refresh exact usage details. This should be evaluated as an additive guidance improvement, not as a replacement for repository-owned help text. The CLI should still explain the local mental model well enough that a caller understands JavaScript is expected to use a PuerTS-style bridge to access Unity and C# APIs.

Alternative considered:
- Avoid any external link and rely only on repository-local help. Rejected for now because an official reference may provide high leverage for agents and humans already familiar with PuerTS.

### Decision: Keep validation focused on faster bridge recognition, not on task-specific persistence checks
For Prompt A, the relevant bridge issue is whether the agent can quickly form the correct JavaScript/C# interaction model. It is not whether the agent performs extra host-side persistence checks on a saved scene. Validation for this change should therefore emphasize reduced bridge probing and faster convergence on correct bridge usage, not file-system confirmation behavior.

Alternative considered:
- Continue using Prompt A persistence confirmation as the main signal for bridge discoverability. Rejected because that conflates bridge guidance with task-specific save semantics.

## Risks / Trade-offs

- [The guidance change may duplicate what examples already imply] -> Compare bridge-specific validation runs before expanding the help surface too broadly.
- [External links may drift or add token cost] -> Treat external references as optional supplements, not the only explanation.
- [Bridge discoverability may still overlap with compile workflow friction] -> Keep linked changes separate and only merge later if new evidence shows they are inseparable.
