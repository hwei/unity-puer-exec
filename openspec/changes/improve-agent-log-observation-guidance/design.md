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

## Risks / Trade-offs

- [The root cause may span contract and help together] → Preserve multiple candidate explanations until targeted evidence narrows them.
