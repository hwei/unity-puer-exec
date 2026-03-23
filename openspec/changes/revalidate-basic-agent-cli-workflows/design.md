## Context

Archived change `validate-help-only-agent-cli-discoverability` defined the repository's two representative baseline tasks: a simple scene-editing workflow and a longer code-write plus verification workflow. Archived change `improve-cli-help-for-agent-efficiency` then reran those tasks and showed that the help surface kept the agent on a more focused command path, but both tasks still landed at `recoverable` rather than `clean`.

This change does not try to redesign the protocol or expand into harder tasks yet. Its purpose is to refresh the baseline against the current CLI while keeping the core comparison inputs stable enough that any movement in the result can still be interpreted. The user also clarified that environment friction belongs inside the product judgment: if the CLI still requires an agent to work around readiness, compile, or observation friction in a non-autonomous way, that is part of the CLI outcome rather than an unrelated external note.

## Goals / Non-Goals

**Goals:**
- Revalidate the current CLI against the original basic workflow prompts without changing the prompt wording.
- Keep the comparison anchor stable by fixing the model to `gpt-5.4-mini subagent` and using sequential runs rather than parallel contention.
- Record results so environment friction that interrupts autonomous completion is scored as part of the CLI effectiveness outcome.
- Preserve the existing durable structured record format while allowing raw transcripts to remain temporary or absent.

**Non-Goals:**
- Do not add a new complex task class in this change.
- Do not move this protocol into `tests/`; it remains an OpenSpec-owned validation workflow rather than a repository regression suite.
- Do not require long-term retention of raw transcripts.
- Do not change the formal CLI contract in this change.

## Decisions

### Decision: Reuse Prompt A and Prompt B without wording changes
The change should continue to use the original scene-editing and code-write-plus-verification prompts from `validate-help-only-agent-cli-discoverability` as the comparison anchor. Keeping the goal wording stable is more important here than refining the tasks, because this round is meant to answer whether the current CLI improved or regressed on the same baseline workflows.

Alternative considered:
- Rewrite the prompts to better match the current CLI. Rejected because that would weaken comparability and make outcome changes harder to attribute.

### Decision: Keep the model fixed to the original validation model
The validating agent should remain `gpt-5.4-mini subagent` for this round so the baseline continues to answer a CLI question instead of collapsing CLI changes and model-capability changes into a single result.

Alternative considered:
- Upgrade the model for a stronger agent baseline. Rejected because it would make the comparison less useful for diagnosing whether the CLI itself improved.

### Decision: Count environment friction inside the result, not outside it
Readiness recovery, compile timing, observation timing, launch conflict handling, and similar workflow friction should be captured as part of the CLI effectiveness judgment when they materially affect autonomous task completion. Operator observation and raw external facts should still be recorded separately, but the final assessment should not excuse product-facing friction merely because the root cause crosses CLI and editor boundaries.

Alternative considered:
- Treat environment friction only as an external contamination note. Rejected because the CLI explicitly aims to absorb these frictions for AI-driven Unity workflows.

### Decision: Keep raw transcript retention optional and temporary
The durable record should remain the structured validation summary in OpenSpec. Raw transcripts may be retained under temporary storage when useful during analysis, but the protocol should not require permanent retention to treat a run as valid evidence.

Alternative considered:
- Make raw transcript retention mandatory for every run. Rejected because it adds storage and workflow overhead without being required for this baseline revalidation round.

## Risks / Trade-offs

- [Stable prompts may miss new CLI-specific regressions] → Accept this for the baseline round and add new task classes only after the basic workflows are reconfirmed.
- [Environment friction can blur product and host causes] → Keep operator observation and modal-blocker notes explicit while still treating unresolved friction as part of the product judgment.
- [Optional raw transcripts reduce later forensic depth] → Preserve the structured command/help/result record as the durable minimum and use temporary raw logs only when needed.
