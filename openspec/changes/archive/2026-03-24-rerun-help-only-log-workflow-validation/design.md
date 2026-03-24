## Context

The archived change `validate-help-only-agent-cli-discoverability` established the durable help-only validation protocol and produced the original Prompt B baseline. The follow-up change `add-log-pattern-workflow-example` then added an ordinary log workflow example specifically because exploratory work showed that agents could discover `wait-for-log-pattern` yet still lacked a canonical workflow for ordinary log verification.

That implementation change cannot also provide its own decisive rerun evidence because the apply session already read repository source, tests, and prior artifacts. This rerun therefore needs to stand alone as a validation-scoped change that reuses the published CLI surface and the earlier Prompt B style task while preserving the original help-only boundary.

## Goals / Non-Goals

**Goals:**
- Re-run one representative log-oriented help-only validation trial against the new published help surface.
- Record whether the agent stayed within CLI-native observation for final confirmation.
- Record whether the agent captured and used `log_offset` as the intended observation checkpoint.
- Produce comparison-ready evidence that can close or extend `add-log-pattern-workflow-example`.

**Non-Goals:**
- Changing CLI behavior, defaults, or help text further.
- Expanding the archived validation protocol into a broader new benchmark suite.
- Deciding or implementing default `log_offset` unless the rerun evidence later justifies a separate change.

## Decisions

### Run a validation-only follow-up change instead of reusing the implementation session

The rerun must preserve the help-only boundary, so it cannot be folded into the session that already inspected repository internals during apply. A standalone validation change keeps the evidence honest and makes the dependency on clean discovery conditions explicit.

Alternative considered:
- Continue directly inside `add-log-pattern-workflow-example`: rejected because the evidence would be contaminated by repository-local context and would not answer the help-only question.

### Reuse the representative Prompt B style workflow as the rerun target

The goal is not to measure general CLI quality again; it is to determine whether the new ordinary log example changes the specific failure mode that previously led to host-log fallback. Reusing the representative log-oriented baseline gives a direct before/after comparison.

Alternative considered:
- Run a fresh or broader task mix: rejected because it would dilute the comparison and make it harder to isolate the effect of the new example.

### Record checkpoint usage and host-log fallback as first-class findings

Task success alone is not enough. The rerun needs to state whether the agent captured `log_offset`, started observation from that checkpoint, and kept final verification inside the CLI surface. Those are the concrete signals needed to decide whether example-first guidance was sufficient.

Alternative considered:
- Judge success based only on whether the Unity-side outcome was achieved: rejected because the key question is workflow choice, not only end-state correctness.

## Risks / Trade-offs

- [A single rerun may still contain trial variance] -> Keep the scope honest and compare against transcript-backed historical evidence rather than overstating certainty.
- [Validation host drift may affect the rerun] -> Reuse the established help-only protocol and record environment-specific friction separately from discoverability findings.
- [The rerun may show mixed results instead of a clean answer] -> Capture checkpoint usage and host-log fallback independently so the next decision can still be grounded in concrete evidence.
