## Why

The newly archived Prompt B compile-recovery rerun still had to fall back to direct `Editor.log` inspection because `wait-for-log-pattern` returned `unity_stalled` twice without giving the validating subagent a clearly published next step that preserved the intended CLI-native verification path.

## What Changes

- Clarify or improve the `wait-for-log-pattern` stalled-outcome recovery path so help-only agents can stay inside the CLI surface more reliably.
- Keep the scope narrow: focus on post-stall guidance and bounded observation behavior, not a general log-observation redesign.
- Validate the result with a follow-up help-only rerun that checks whether direct `Editor.log` fallback decreases.

## Capabilities

### Modified Capabilities
- `agent-cli-discoverability-validation`: log-observation reruns can measure whether `unity_stalled` remains a common reason that agents leave the intended CLI verification surface.

## Impact

- Targets the main remaining regression observed in the latest Prompt B evidence after compile-recovery guidance improved.
- Keeps the follow-up small enough for a focused next session.
