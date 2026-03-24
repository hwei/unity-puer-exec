## Why

Prompt B still contains a help-surface discoverability footgun: top-level help lists workflow names such as `exec-and-wait-for-log-pattern`, but those names are example identifiers rather than executable subcommands. A validating agent can waste a step trying to invoke the workflow name directly before discovering that it belongs behind `--help-example`.

## What Changes

- Clarify the published help surface so example workflow names are visibly distinguished from real commands.
- Make the discovery path from top-level help to `--help-example <id>` explicit for workflow-style entries.
- Validate the change with a `gpt-5.4-mini subagent` Prompt B rerun that compares help usage against the archived baseline.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: Prompt B help-only reruns can evaluate whether workflow-example discoverability improved without mutating Prompt B wording.

## Impact

- Reduces avoidable top-level help confusion during Prompt B style log-verification work.
- Keeps the fix scoped to help discoverability rather than changing the underlying Prompt B task.
- Produces transcript-backed Prompt B evidence about whether the new help wording removes one first-pass wrong turn.
