## Context

The upstream exploration in `improve-agent-log-observation-guidance` narrowed the problem substantially. Current help already tells agents that `wait-for-log-pattern` is the log-observation primitive, and validation evidence shows agents can discover that command. The remaining gap is workflow-shaped: the published long-workflow example set includes `exec-and-wait-for-result-marker`, but not a parallel ordinary log-pattern path. That leaves agents to synthesize checkpoint capture, `--start-offset`, and observation retry behavior on their own.

This change exists to implement the smallest credible guidance improvement before considering a contract-level change such as default `log_offset`.

## Goals / Non-Goals

**Goals:**
- Add a first-class ordinary log workflow example that is discoverable through the published help surface.
- Make the intended checkpointed `exec -> wait-for-log-pattern` path explicit enough that agents do not need to invent it from scattered help fragments.
- Validate whether that example-first improvement materially reduces host-log fallback in the representative log-verification baseline.

**Non-Goals:**
- Do not change `exec` to return `log_offset` by default in this change.
- Do not redesign the overall command model for long-running observation.
- Do not broaden this work into unrelated compile-recovery or startup-continuity changes.

## Decisions

### Decision: Add a dedicated ordinary log workflow example
The help surface should expose a named `--help-example` workflow for ordinary log verification, not just command-level prose. This keeps ordinary log waiting symmetric with the existing result-marker example and gives agents a single canonical path to copy.

Alternative considered:
- Strengthen only `wait-for-log-pattern --help`. Rejected because command help alone still leaves the multi-step workflow fragmented.

### Decision: Keep the example centered on checkpoint capture
The example should show `exec --include-log-offset` followed by `wait-for-log-pattern --start-offset ...` so the canonical path explicitly avoids a full-log scan and avoids a missed-window fallback.

Alternative considered:
- Show a simpler example without `log_offset`. Rejected because that would fail to teach the key workflow behavior this change is trying to normalize.

### Decision: Pair the example with minimal supporting top-level guidance
The top-level workflow list and relevant command cross-references should mention the ordinary log example so agents can discover it from the same surfaces that already route them to `exec-and-wait-for-result-marker`.

Alternative considered:
- Add the example without any surrounding discoverability updates. Rejected because the new example would be weaker if it remained buried behind direct example-id recall.

### Decision: Validate against the representative log-verification baseline before revisiting contract defaults
The follow-up validation should focus on whether the log-oriented baseline converges through the intended CLI observation path more cleanly than before. Only if fallback remains concentrated on omitted checkpoint capture should the repository revisit default `log_offset`.

Alternative considered:
- Combine the example change with default `log_offset` immediately. Rejected because that would prevent clean attribution of any validation improvement.

## Risks / Trade-offs

- [Agents may still ignore the new example and rely on command help only] -> Mention the new example from top-level workflow surfaces and related command help.
- [The example may overfit one Prompt B style task] -> Keep it phrased as ordinary log verification rather than as a task-specific menu-validation recipe.
- [Validation may improve only from cleaner prompting rather than better workflow guidance] -> Reuse the archived baseline task wording and compare against earlier transcript-backed evidence.

## Migration Plan

1. Add the new workflow example and related help-surface references.
2. Update help-rendering tests to cover the new example and its discoverability hooks.
3. Re-run the relevant representative validation and record whether host-log fallback decreases.
4. Reassess whether any contract-level follow-up is still needed.

## Open Questions

- Should the example id be `exec-and-wait-for-log-pattern` or a name that emphasizes verification rather than command sequence?
- How much recovery detail should the example include before it becomes too long for a canonical help surface?
