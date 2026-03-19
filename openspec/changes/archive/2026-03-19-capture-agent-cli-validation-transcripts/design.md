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

### Decision: Use a stable structured record with a small required schema
Each validation run will produce a structured transcript record that keeps the fields needed for later comparison:

- `prompt_id`: ties the run to a specific task prompt
- `model`: identifies which agent or model produced the behavior
- `constraints`: records the allowed and disallowed discovery boundaries
- `help_queries`: records which help surfaces the agent actually consulted
- `command_trace`: records the key CLI commands that materially advanced the run
- `key_outputs`: records the output excerpts used to justify the result
- `task_success`: records whether the Unity-side goal was achieved
- `autonomy`: records whether the run stayed inside the allowed discovery surface
- `efficiency`: records whether convergence was clean, recoverable, or poor
- `findings`: records concrete discoverability observations for later product work

The schema intentionally stays small. It is meant to preserve decision-relevant evidence, not every byte of process output.

Alternative considered:
- Store only free-form narrative notes. Rejected because later reviewers could not reliably compare runs across prompts or help revisions.

### Decision: Record operator-observed blockers separately from agent behavior
`human_intervention` and `modal_blocker` will be recorded as operator-authored observation fields rather than as agent-self-reported facts.

- `human_intervention` records whether the operator merely observed the run or performed a non-decisive or decisive intervention.
- `modal_blocker` records whether a Unity-native modal interrupted the run, how it was detected, and how it was resolved.

These fields are necessary because current product surfaces do not yet expose machine-readable modal blocker detection, and a run can be distorted by operator action without that being visible in the CLI transcript alone.

Alternative considered:
- Infer these fields entirely from command logs. Rejected because the current product cannot distinguish a save-scene modal from a generic stall with enough confidence.

### Decision: Split raw transcript storage from durable OpenSpec summaries
Long raw transcripts should live under `.tmp/agent-validation-transcripts/` so repeated trial logs do not bloat change artifacts. The change directory will hold:

- the protocol and template that define what must be recorded
- selected structured transcript examples
- short summaries that point to the retained raw evidence location when it still exists

Alternative considered:
- Store all raw transcripts directly inside the change directory. Rejected because repeated validation runs would quickly make the change artifacts noisy and heavy.

## Risks / Trade-offs

- [Transcript capture may feel heavy for manual runs] → Keep the minimum required fields small and focus on key steps rather than every byte of output.
- [Different operators may record transcripts inconsistently] → Define a standard template and stable required fields.
- [Semi-manual capture may still miss some decision context] → Treat this as an evidence floor that can later be automated by a harness change.
- [Raw `.tmp` evidence may be deleted before later review] → Require the structured record to retain enough key commands and outputs to remain useful even when temporary raw logs are gone.
