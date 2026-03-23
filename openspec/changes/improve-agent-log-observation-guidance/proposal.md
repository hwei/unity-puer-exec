## Why

The current validation evidence suggests a distinct agent-usage gap around log-oriented workflows: even when the CLI already exposes `wait-for-log-pattern` and `wait-for-result-marker`, agents may still fall back to ad hoc host-log inspection instead of using the intended CLI observation surface. This needs its own exploration path so help, examples, and workflow guidance can be evaluated independently from compile-recovery or editor-interaction issues.

## What Changes

- Explore how agents currently discover and choose between `wait-for-log-pattern`, `wait-for-result-marker`, and host-side log inspection.
- Define the high-level improvement goal for making the intended log-observation workflow easier for agents to follow.
- Capture follow-up design questions and validation targets without committing to an implementation in this change yet.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: log-observation workflow guidance may need to become more explicit for agent callers.
- `agent-cli-discoverability-validation`: validation may need targeted evidence for whether agents follow the intended log-observation surface.

## Impact

- Affects help, examples, and workflow guidance for log-based observation.
- May later affect validation prompts or evidence collection focused on result-marker and log-pattern usage.
- This change is intentionally exploration-first and does not yet commit to code changes.
