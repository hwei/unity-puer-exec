## Context

`brief_sequence` is currently defined as a literal character-per-brief summary. That is simple but scales badly during import-heavy or compile-heavy phases, where the same brief kind can repeat thousands of times. The validation run that installed the OpenUPM package produced exactly that shape of output.

## Goals / Non-Goals

**Goals:**
- Reduce response size and scanning cost for long repeated observation runs.
- Preserve deterministic machine parsing.

**Non-Goals:**
- Replace `get-log-briefs` with a new rich summary format.
- Remove the ability to understand the underlying brief kinds.

## Decisions

### Decision: Use a compact run encoding instead of literal repetition

A compact encoding like `WI32E2I` keeps the original order and kinds visible while reducing repeated runs substantially.

### Decision: Keep single-count runs concise

Runs of length 1 should stay as a bare character so short sequences remain easy to read.

## Risks / Trade-offs

- [Risk] Consumers that assumed literal repetition will need adjustment. Mitigation: update durable spec truth and targeted tests together.
