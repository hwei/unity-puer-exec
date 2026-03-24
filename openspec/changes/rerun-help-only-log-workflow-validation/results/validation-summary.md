## Summary

The clean help-only rerun answered the main question of `add-log-pattern-workflow-example`: the validating subagent consulted the new `exec-and-wait-for-log-pattern` example, captured `log_offset` from the verifying `exec`, and completed final confirmation through `wait-for-log-pattern --start-offset ...` without falling back to direct `Editor.log` inspection.

## Comparison Against Earlier Prompt B Evidence

- `2026-03-19` transcript-backed baseline: Prompt B already showed that the CLI could support a real multi-step workflow, but exact checkpoint usage was not durably preserved.
- `2026-03-20` post-help baseline: Prompt B converged through `exec --include-log-offset` plus `wait-for-log-pattern --start-offset ...`, but still remained `recoverable` because the first wait started too late and required a second attempt.
- `2026-03-23` current baseline: Prompt B stayed autonomous yet escaped the intended observation surface by using direct `Editor.log` inspection for final confirmation.
- `2026-03-24` rerun in this change: Prompt B consulted `exec-and-wait-for-log-pattern`, used the CLI-native checkpoint path, and kept final verification inside the published observation surface.

## Decision

The example-first help change appears sufficient for the specific gap investigated here. The rerun removed the earlier host-log fallback and showed that a clean help-only agent can now use the ordinary log workflow as intended.

`default log_offset` does not currently appear justified as an immediate follow-up. The remaining friction in this rerun was not a missed checkpoint; it was ordinary workflow setup around choosing a deterministic selected asset and waiting for Unity recovery.
