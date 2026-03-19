## Why

Archived change `validate-help-only-agent-cli-discoverability` already showed that a `gpt-5.4-mini subagent` could complete real tasks through the published CLI help surface without repository-only hints. That validation also showed an efficiency gap: the agent succeeded, but still spent a small amount of time probing before converging on the shortest workflow.

The later transcript-focused change `capture-agent-cli-validation-transcripts` exists because the first-round validation preserved only result summaries and command families, which was not enough detail to confidently tune the help surface. This follow-up change exists to improve CLI help efficiency using that evidence chain rather than maintainer intuition.

## What Changes

- Refine the published CLI help surface to reduce unnecessary exploration and make the preferred workflow more immediately obvious.
- Use transcript-backed validation findings from `capture-agent-cli-validation-transcripts`, grounded in the earlier success criteria from `validate-help-only-agent-cli-discoverability`, to target the highest-friction discovery points first.
- Re-run validation after the help changes to measure whether convergence becomes cleaner.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: help should more directly guide agents toward the shortest effective project-scoped workflow.
- `agent-cli-discoverability-validation`: validation should compare pre- and post-help-change efficiency using transcript-backed evidence.

## Impact

- Affects `unity-puer-exec` help and example design.
- Affects validation interpretation for agent discoverability and efficiency.
- Depends on the archived finding that help-only subagent execution already works and on transcript capture that makes the remaining efficiency gap analyzable.
