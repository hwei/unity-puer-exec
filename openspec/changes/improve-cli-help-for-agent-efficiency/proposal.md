## Why

The first help-only validation showed that agents can complete real tasks through the published CLI surface, but they still spend a small amount of time probing before converging. We want the help surface to guide medium-capability agents toward the intended workflow faster, using transcript-backed evidence rather than guesswork.

## What Changes

- Refine the published CLI help surface to reduce unnecessary exploration and make the preferred workflow more immediately obvious.
- Use transcript-backed validation findings to target the highest-friction discovery points first.
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
- Depends on better transcript evidence so help revisions can be justified by observed agent behavior.
