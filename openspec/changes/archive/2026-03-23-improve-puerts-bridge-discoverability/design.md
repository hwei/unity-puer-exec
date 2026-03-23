## Context

Recent agent-validation results narrowed one recurring source of friction: agents can often complete the target workflow, but they first spend time inferring how JavaScript is supposed to talk to Unity and C# inside `exec`. The current help surface hints at the bridge shape through examples like `puer.loadType(...)`, yet it does not clearly label that bridge model as PuerTS-style usage or point callers toward a concise bridge-oriented explanation.

One concrete sub-case is now worth recording explicitly. Prompt A no longer appears blocked on startup behavior, but the validating agent still needed to correct a verification script after treating a bridged Unity-side collection shape too much like an ordinary JavaScript array. That kind of confusion is not unique to agents; it is a known source of friction for humans using PuerTS as well. The CLI help therefore may need to do more than name PuerTS. It may need to warn callers that bridged C# arrays and generic lists are not automatically interchangeable with native JS arrays, and point to a concise reference for the correct access patterns.

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
- Decide whether collection-specific guidance should explicitly warn that C# `Array` / `List<T>` semantics are not the same as ordinary JavaScript arrays.
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

The current most relevant reference for this change is the PuerTS Unity guide for JavaScript calling C#, because it already covers the local bridge concepts the CLI depends on, including `CS.*`, `puer.$generic(...)`, and related bridge helpers:

- https://puerts.github.io/docs/puerts/unity/tutorial/js2cs

This link is especially relevant when the caller needs to reason about bridged C# collection and type semantics rather than ordinary JavaScript object semantics.

Alternative considered:
- Avoid any external link and rely only on repository-local help. Rejected for now because an official reference may provide high leverage for agents and humans already familiar with PuerTS.

### Decision: Record bridged collection semantics as a first-class guidance gap
This change should not stop at generic “bridge discoverability”. The current Prompt A evidence suggests a more specific friction point: callers may assume bridged C# arrays or generic lists behave like normal JS arrays, even though PuerTS requires a different mental model for some access and construction patterns. The guidance work should therefore evaluate whether the CLI help needs a short explicit warning such as:

- C# arrays and `List<T>` are bridged objects, not plain JS arrays
- prefer PuerTS-aware access patterns and type construction rules
- consult the official JS-to-C# guide when array/list behavior is not obvious

Alternative considered:
- Treat collection semantics as too low-level for CLI help. Rejected for now because this exact confusion is now part of the remaining Prompt A friction and appears important enough to justify at least a short warning plus a reference.

### Decision: Keep validation focused on faster bridge recognition, not on task-specific persistence checks
For Prompt A, the relevant bridge issue is whether the agent can quickly form the correct JavaScript/C# interaction model. It is not whether the agent performs extra host-side persistence checks on a saved scene. Validation for this change should therefore emphasize reduced bridge probing and faster convergence on correct bridge usage, not file-system confirmation behavior.

Alternative considered:
- Continue using Prompt A persistence confirmation as the main signal for bridge discoverability. Rejected because that conflates bridge guidance with task-specific save semantics.

## Risks / Trade-offs

- [The guidance change may duplicate what examples already imply] -> Compare bridge-specific validation runs before expanding the help surface too broadly.
- [External links may drift or add token cost] -> Treat external references as optional supplements, not the only explanation.
- [Bridge discoverability may still overlap with compile workflow friction] -> Keep linked changes separate and only merge later if new evidence shows they are inseparable.
- [Collection-specific guidance may become too detailed for top-level help] -> Keep the main warning short and use an external PuerTS reference for the deeper explanation.

## Evidence Review

### Prompt A evidence: the remaining friction is bridge-shape probing, not startup continuity

The latest Prompt A durable record shows that the validating agent stayed on the intended CLI path:

- it started from published help plus normal CLI execution only
- it used `exec` as the primary project-scoped command
- it completed the run through the accepted `running -> wait-for-exec` lifecycle
- it did not branch back to the old explicit `wait-until-ready` startup recovery path

The same record also shows why the run remained only `recoverable`: before the final scene-editing verification converged, the agent first executed a context-inspection probe and then a Unity-type probe to infer the bridge shape. The durable record explicitly notes that the remaining friction was "verification-side bridge and reflection discovery rather than startup continuity."

This means Prompt A is now valid evidence for a bridge-focused follow-up change. The current slowdown is no longer primarily about startup, persistence confirmation, or compile recovery.

### Standard Prompt C evidence: compile recovery is clean, but bridge usage is still only indirectly discoverable

The latest Standard Prompt C durable record shows that the agent now reaches a clean compile-and-call flow:

- it discovered `--refresh-before-exec` from help without maintainer hints
- it accepted `running` with `phase = compiling`
- it continued the same request through `wait-for-exec`
- it completed verification with `result.value = 12`

That record is still relevant to this change because its help-query sequence includes one explicit bridge-oriented discovery step: the agent consulted `--help-example request-editor-exit-via-exec` to confirm that `puer.loadType(...)` is the expected JavaScript-to-C# bridge shape.

The Prompt C evidence therefore supports a narrower conclusion than Prompt A:

- bridge discoverability is not currently severe enough to prevent eventual success on the cleaner compile-and-call workflow
- but the help surface still exposes bridge usage mostly through incidental examples rather than through an explicit bridge mental model

### Recorded collection-specific confusion

Prompt A already provides enough durable evidence to treat collection semantics as a first-class sub-problem. The validating agent needed to correct verification logic after initially treating a bridged Unity-side collection too much like an ordinary JavaScript array. This is the concrete reason the change should evaluate a short collection warning instead of discussing bridge discoverability only in abstract terms.

The product implication is narrow but important:

- callers need to understand that bridged C# arrays and `List<T>` values are .NET-backed bridge objects
- callers should not assume native JS-array methods, construction patterns, or mutation expectations apply unchanged
- when array or generic-list behavior matters, help should point callers toward a PuerTS-specific JS-to-C# reference rather than leaving them to infer semantics through trial and error

## Current Help Surface Inventory

### What the current help surface already communicates

The published help already gives agents several useful signals:

- top-level help makes `exec` the primary project-scoped workflow
- `exec --help-args` explains selector rules, script-source flags, and the required module-shaped entry function
- `exec --help-status` explains the accepted `running` continuation path
- `--help-example request-editor-exit-via-exec` contains a concrete `puer.loadType('UnityEditor.EditorApplication')` example

These signals are sufficient for an agent that already recognizes the PuerTS pattern or is willing to probe for it.

### What remains too implicit

The same help surface still leaves the bridge model under-specified:

- top-level help does not explicitly name PuerTS
- `exec` help explains script shape and lifecycle but not how JavaScript is expected to access Unity or C# APIs
- bridge access is shown only inside a single workflow example rather than in a dedicated bridge-oriented section
- help does not mention `globalThis.CS`, `puer.$generic(...)`, or any concise mental model for bridged .NET types
- help does not warn that bridged C# arrays and generic lists are not plain JS arrays

This explains the observed probing behavior: agents can find a valid bridge example, but they must first infer whether it is merely an example-specific idiom or the actual intended product model.

## Guidance Direction

### Candidate guidance improvements

The current evidence supports comparing four additive guidance layers:

1. Explicit terminology
   State directly that `unity-puer-exec` scripts use a PuerTS-style JavaScript-to-C# bridge.
2. Short bridge mental model
   Add a compact explanation that Unity and C# APIs are accessed as bridged .NET types rather than as ordinary JS modules or plain JSON-like objects.
3. Stronger examples
   Add or revise help examples so bridge usage appears in a purpose-built bridge section, not only in a workflow-specific exit example.
4. Official reference link
   Keep a short repository-owned explanation, then optionally link to the official PuerTS JS-to-C# guide for callers who need exact bridge rules.

### Decision: put the minimum mental model in CLI help

The minimum bridge model belongs in CLI help, not only in external references or user-authored skills. Agents currently restrict themselves to the published CLI help surface during validation, so a help-only run should not require external ecosystem recall before the caller can form the right model.

The CLI-owned minimum should cover:

- this is a PuerTS-style bridge
- `puer.loadType(...)` is a normal way to load Unity/C# types
- bridged .NET values are not always interchangeable with ordinary JS values

### Decision: keep deeper bridge detail outside top-level help

Detailed bridge catalog material does not belong in top-level `--help`. The richer details should remain in one of these lower-cost surfaces:

- a dedicated `exec` help/example section
- an official external PuerTS reference link
- optional repository-owned skills for richer task-specific authoring patterns

This keeps top-level help short while still giving agents a discoverable path to bridge-specific details.

### Decision: include a short collection warning plus the official reference link

The collection-specific confusion is concrete enough that the help surface should include a short warning. The recommended shape is intentionally concise:

- bridged C# arrays and `List<T>` values are not plain JS arrays
- prefer PuerTS-aware access and construction patterns when working with those values
- consult the official JS-to-C# reference when behavior is not obvious

That warning should live near the bridge mental-model guidance, not be buried only in a long example.

## Validation Framing

### Measure faster bridge recognition directly

Future validation for this change should ask whether the agent recognized and applied the intended bridge model quickly, not merely whether it eventually finished the business task.

The comparison should therefore record:

- whether the agent needed extra bridge-probing exec calls before the main task converged
- whether the agent consulted a bridge-specific help/example surface directly instead of inferring from unrelated examples
- whether the first serious verification script already used the intended bridge model
- whether any remaining retries were caused by bridge semantics rather than compile recovery, startup continuity, or persistence checks

### Keep bridge validation separate from other workflow questions

Bridge-discoverability validation should not be scored by:

- whether `--refresh-before-exec` was needed or discovered
- whether Unity startup continuity stayed on the accepted primary path
- whether the agent performed extra host-side file checks after a scene save

Those behaviors belong to other changes and would make this change's evidence harder to interpret.

## Follow-up Implementation Targets

If the exploration conclusions above hold, the most likely implementation targets are:

- add a bridge-oriented help section to the `exec` surface or top-level workflow help
- add one bridge-focused example that demonstrates loading and calling a Unity/C# type for a non-exit workflow
- add a short warning about bridged C# array and `List<T>` semantics
- attach the official PuerTS JS-to-C# reference link as a supplement, not as the sole explanation
- extend help-surface validation artifacts so future reruns can score bridge recognition separately from compile recovery and persistence confirmation

This change does not yet justify a new runtime command, bridge-specific API wrapper, or larger execution-surface redesign.

## Implementation Scope

### Decision: implement the bridge guidance in the existing help surface

The next slice should update the existing CLI help surface rather than inventing a new command family. The minimum implementation scope is:

- top-level or `exec` help explicitly names the PuerTS-style bridge model
- the help surface includes a short bridge mental model near script authoring guidance
- the help surface warns that bridged C# arrays and `List<T>` values are not plain JS arrays
- the help surface includes one purpose-built bridge example or bridge-oriented example notice
- the help surface links to the official JS-to-C# reference as a supplement

### Decision: keep the implementation anchored to help-only validation

This implementation should remain justifiable through the same help-only validation protocol already used elsewhere in the repository. That means the implementation should prefer small, publishable help changes that are easy to validate against Prompt A and Standard Prompt C, rather than a broad documentation expansion that only humans will read outside the CLI.
