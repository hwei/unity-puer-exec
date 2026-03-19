## Context

The repository already separates durable governance requirements from machine-readable backlog metadata, but recent follow-up work showed a gap between those layers. `improve-cli-help-for-agent-efficiency` depends on a specific evidence chain: help-only subagent validation proved the CLI was usable, that validation also showed extra probing before convergence, and a later transcript-capture change existed so the next help iteration could target observed friction instead of guesswork. That chain can be reconstructed from archived artifacts, but the follow-up change does not name it clearly enough for a fresh reader to recover the rationale from the current change documents alone.

`meta.yaml` is not the right place to solve that gap by itself. Metadata can say that one change is blocked by another, but it cannot explain which findings matter, whether the predecessor established success versus failure, or what exact conclusion the new change inherits. The fix belongs in governance rules for proposal and design authorship, while keeping metadata machine-readable and lightweight.

## Goals / Non-Goals

**Goals:**
- Make follow-up changes self-traceable when prior experiments or findings are necessary to understand scope.
- Keep `meta.yaml` focused on sortable planning state rather than turning it into a second narrative artifact.
- Reduce ambiguity when active and archived change records coexist or when a follow-up change depends on archived findings.

**Non-Goals:**
- Do not require every change to restate all repository history.
- Do not promote archived findings into durable product requirements unless they truly change long-lived behavior.
- Do not replace backlog tooling with prose-only governance checks.

## Decisions

### Decision: Require narrative upstream context in proposal/design, not only metadata
Follow-up changes should explicitly cite the upstream change names and summarize the specific findings they inherit whenever those findings are necessary to understand the new scope.

Alternative considered:
- Rely on `meta.yaml.blocked_by` alone. Rejected because dependency names do not explain what was learned or why the dependency matters.

### Decision: Keep `meta.yaml` machine-readable and narrow
`meta.yaml` should continue to represent planning state, ranking inputs, and prerequisite references, but governance should state that it is insufficient as the sole background mechanism for dependent work.

Alternative considered:
- Expand `meta.yaml` to carry narrative evidence summaries. Rejected because it would duplicate proposal/design content and make structured metadata less stable.

### Decision: Add a governance requirement for evidence-chain traceability
The durable rule should target cases where a reader cannot correctly understand the current change without knowing prior validation or retrospective findings.

Alternative considered:
- Treat missing context as an informal review smell only. Rejected because the same omission can recur unless the repository makes the expectation explicit.

## Risks / Trade-offs

- [Traceability requirements may bloat small changes] -> Limit the rule to prerequisite context that is necessary for understanding scope, not all historical detail.
- [Metadata and narrative references may drift] -> Keep metadata narrow and require proposal/design to cite concrete upstream change names and findings.
- [Archived and active records may still confuse readers] -> Use this change to make the lifecycle expectation explicit, then decide separately whether tooling should detect duplicate active/archive visibility.
