## Why

The change `add-log-pattern-workflow-example` added a first-class ordinary log verification example, but its key question is still unresolved: whether a clean help-only agent rerun now keeps final confirmation inside the CLI observation surface instead of falling back to direct host-log inspection. We need a separate validation-only change because the implementation session that added the example already consumed repository-local context and cannot serve as a valid help-only trial.

## What Changes

- Re-run the representative log-oriented help-only agent validation after the new `exec-and-wait-for-log-pattern` example was published.
- Record whether the rerun uses the intended `exec --include-log-offset` plus `wait-for-log-pattern --start-offset ...` workflow for final confirmation.
- Compare the rerun against earlier Prompt B style transcript-backed baselines, with special attention to host-log fallback and checkpoint usage.
- Capture the conclusion needed by `add-log-pattern-workflow-example`: whether example-first guidance was sufficient on its own, or whether contract-level follow-up such as default `log_offset` still merits exploration.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: extend the validation requirements so ordinary log-workflow help changes are judged against transcript-backed rerun evidence that explicitly records checkpoint usage and host-log fallback.

## Impact

- Affects OpenSpec validation artifacts and repository-owned validation evidence for the representative log-oriented baseline.
- Affects closeout evidence for `add-log-pattern-workflow-example`.
- Does not change product behavior, CLI contract defaults, or repository tests by itself.
