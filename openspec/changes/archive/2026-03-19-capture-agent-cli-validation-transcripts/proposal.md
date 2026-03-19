## Why

The first help-only agent validation proved the CLI is usable, but the repository only retained summarized results rather than full behavior traces. Without durable transcript capture, future efficiency work will be driven by memory and anecdotes instead of comparable evidence.

## What Changes

- Define a repository-owned transcript capture format for agent CLI validation runs.
- Require validation runs to retain the prompt, key command sequence, and key observed outputs in durable records.
- Establish where those transcript artifacts live and what minimum fields they must contain.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: validation runs should retain durable transcript evidence in addition to summarized task outcomes.

## Impact

- Affects how future help-only agent validation runs are recorded and reviewed.
- Improves comparability across models, prompts, and help-surface revisions.
- Creates the evidence base for later CLI efficiency improvements and harness work.
