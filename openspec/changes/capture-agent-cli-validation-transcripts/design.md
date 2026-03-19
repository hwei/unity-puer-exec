## Context

The archived help-only validation captured results and findings, but not the full sequence of agent actions. That makes it hard to answer questions such as which help commands were read first, how many wrong turns occurred, and whether later help changes actually reduce exploration.

This belongs in the durable validation capability because transcript capture is part of the repository's repeatable evaluation method, not just an ad hoc operator note.

## Goals / Non-Goals

**Goals:**
- Define the minimum durable transcript record for each validation trial.
- Make transcript capture lightweight enough to use in repeated manual or semi-manual runs.
- Keep transcript evidence separate from high-level result summaries.

**Non-Goals:**
- Do not require a full automated harness in this change.
- Do not mandate one specific logging implementation if the stored evidence satisfies the protocol.
- Do not optimize CLI help content directly in this change.

## Decisions

### Decision: Require minimum transcript fields, not a single capture mechanism
The change will require durable storage of the prompt, help commands consulted, key command sequence, and outcome-relevant outputs. It will not yet require a fully automated recorder.

Alternative considered:
- Require only final summaries. Rejected because summaries lose the evidence needed for efficiency analysis.

### Decision: Keep transcripts adjacent to validation results
Transcript artifacts should live with the validation change or later validation harness outputs so result summaries and behavior traces can be reviewed together.

Alternative considered:
- Store transcripts in a separate unrelated log area. Rejected because it weakens the connection between trial result and evidence.

## Risks / Trade-offs

- [Transcript capture may feel heavy for manual runs] → Keep the minimum required fields small and focus on key steps rather than every byte of output.
- [Different operators may record transcripts inconsistently] → Define a standard template and stable required fields.
- [Semi-manual capture may still miss some decision context] → Treat this as an evidence floor that can later be automated by a harness change.
