## Context

The repository already has formal CLI surfaces for `wait-for-log-pattern` and `wait-for-result-marker`, but recent validation still showed an agent leaving the CLI surface and reading `Editor.log` directly. That does not yet prove the contract is wrong; it may instead indicate that the current guidance is too weak, too indirect, or too hard to rediscover under task pressure.

## Goals / Non-Goals

**Goals:**
- Clarify why an agent would still leave the intended CLI observation surface when log-oriented verification is needed.
- Identify whether the main issue is help discoverability, recommended examples, command outputs, or command ergonomics.
- Prepare a follow-up implementation direction without prematurely choosing one.

**Non-Goals:**
- Do not implement the final help or contract changes in this change yet.
- Do not mix this exploration with unrelated startup or compile-recovery work.

## Decisions

### Decision: Keep this change exploratory
This change should first explain why agents miss or abandon the intended log-observation commands before any implementation is chosen.

Alternative considered:
- Jump straight into help rewrites. Rejected because the current evidence is still too coarse to prove what specific guidance failed.

### Decision: Treat ordinary log-pattern verification as the leading gap
The strongest remaining gap is not top-level command discovery. Agents can already find `wait-for-log-pattern`, but the current help surface still gives them only one first-class long-workflow example: `exec-and-wait-for-result-marker`. For ordinary log-oriented verification, agents are still expected to assemble the workflow themselves from command help, including checkpoint capture and `--start-offset` usage.

Alternative considered:
- Treat the problem primarily as missing command discoverability. Rejected because multiple validation runs already show agents finding the relevant commands and consulting their help.

### Decision: Prefer an example-first follow-up
The most credible next implementation step is to add a first-class ordinary log-observation workflow example that shows `exec`, log checkpoint capture, and `wait-for-log-pattern --start-offset ...` as one coherent path. This targets the current gap more directly than changing response payload defaults before guidance is revalidated.

Alternative considered:
- Change `exec` to return `log_offset` by default immediately. Deferred because that changes the formal async-observation contract and should be evaluated only after stronger ordinary log-workflow guidance is tested.

### Decision: Keep default `log_offset` as a reserved candidate, not the current recommendation
Returning `log_offset` by default remains a plausible follow-up if agents still miss the checkpoint step after a stronger canonical example exists. It should stay explicitly on the table, but it is no longer the preferred first move.

Alternative considered:
- Reject default `log_offset` entirely. Rejected because the repository has not yet run the cleaner example-first validation needed to prove that stronger workflow guidance alone is sufficient.

## Decision Matrix

### Candidate A: Add an ordinary log-pattern workflow example
- Fixes: lack of a first-class long-workflow pattern for non-result-marker verification
- Strength: directly addresses the current example asymmetry between result-marker and ordinary log waiting
- Validation signal: agents stop falling back to host-log inspection while following the published example-first path

### Candidate B: Strengthen command-level recovery guidance only
- Fixes: missing local reminders about `--include-log-offset`, `--start-offset`, and retry shape
- Strength: lighter-weight than a contract change
- Weakness: still forces agents to compose the full workflow themselves under task pressure

### Candidate C: Return `log_offset` by default
- Fixes: agents forgetting to request a checkpoint explicitly
- Strength: reduces one easy-to-miss step for both result-marker and log-pattern workflows
- Weakness: changes the default contract before guidance has been revalidated

Chosen current direction: Candidate A first, Candidate C only if A does not materially reduce fallback behavior.

## Risks / Trade-offs

- [The root cause may span contract and help together] → Preserve multiple candidate explanations until targeted evidence narrows them.
- [Example-first validation may improve behavior without fully eliminating missed checkpoints] → Keep default `log_offset` available as the next contract-level candidate if fallback remains concentrated on omitted checkpoint capture.
- [A new ordinary log example could still be ignored if command help remains too weak] → Future implementation work should pair the example with concise command-level reminders rather than treating the example as the only surface.

## Open Questions

- Should the eventual ordinary log workflow example be framed as `exec-and-wait-for-log-pattern` or with another name that more clearly distinguishes result-marker from generic log verification?
- How explicit should the example be about recovery after a missed observation window versus keeping the main path minimal?
- What validation threshold is strong enough to rule out default `log_offset` as a necessary follow-up?
