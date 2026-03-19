## Transcript Capture Guide

This change adds a durable transcript floor for help-only agent validation. The goal is to preserve enough evidence to compare runs later without forcing operators to keep every raw byte forever.

## Storage Split

- Keep long raw logs under `.tmp/agent-validation-transcripts/`.
- Keep durable structured records and short summaries in the OpenSpec change or later archived validation artifacts.
- If a raw log exists, the durable record should point to it.
- If a raw log does not exist, the durable record must explicitly say so instead of implying full capture.

## Recorder Responsibilities

The operator or controlling maintainer owns transcript capture. Do not rely on the validating agent to be the sole recorder of its own behavior.

The recorder should:

1. Preserve the task prompt identifier and prompt source.
2. Record the model or agent label used for the run.
3. Record the allowed and disallowed discovery boundaries.
4. Capture the key help queries and key command sequence.
5. Keep the outputs that justify the final outcome and efficiency judgment.
6. Record operator observations that the CLI cannot currently report reliably, including human intervention and Unity-native modal blockers.

## Minimum Capture Standard

A run is considered durably recorded only if the structured record contains:

- prompt identity
- model identity
- constraints
- help queries
- key command trace
- key outputs
- task success
- autonomy
- efficiency
- human intervention
- modal blocker
- findings
- raw transcript status

## Retrospective Records

Some earlier validation runs were only preserved as summaries. Those runs may still be brought into the durable record set as `retrospective-summary` entries if they:

- clearly identify that exact raw transcript data was not retained
- avoid inventing exact commands that were not durably preserved
- preserve the known help surfaces, command families, outcomes, and operator observations

## Recommended Raw Log Layout

Use a stable `.tmp` path layout during future live-captured runs:

```text
.tmp/agent-validation-transcripts/<date>/<prompt-id>-<model>.md
```

The raw log can be a simple operator-maintained running note, as long as the durable YAML record points to it.
