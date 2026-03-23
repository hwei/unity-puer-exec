## Why

Archived and current agent-validation evidence now agrees on the same product gap: the CLI can get a medium-capability agent to eventual success on the basic workflows, but it still does not consistently keep verification inside a clean, machine-usable CLI path. Prompt A still needed host-asset confirmation after startup and bridge-shape friction, and Prompt B still fell back to direct host-log inspection after compile and selection-timing friction.

## What Changes

- Improve the formal CLI verification workflow so agents can confirm basic workflow outcomes without leaving the intended CLI observation surface.
- Define the product-facing contract for verification-oriented follow-up after project-scoped `exec`, especially when compilation, selection timing, or delayed log emission make first-pass confirmation difficult.
- Evaluate Prompt A and Prompt B as separate acceptance tracks while still targeting the shared verification-closure problem first.
- Update validation guidance and representative evidence so future agent-evaluation rounds can distinguish clean CLI verification from host-side fallback confirmation.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: basic project-scoped verification workflows should provide a cleaner CLI-native confirmation path after `exec`.
- `agent-cli-discoverability-validation`: baseline agent validation should explicitly distinguish clean CLI verification from host-side fallback confirmation and track Prompt A/B separately.

## Impact

- Affects CLI contract and help around post-`exec` verification workflows.
- Affects validation interpretation for whether a basic workflow stayed inside the intended CLI observation surface.
- May affect runtime observation plumbing, help examples, and validation harness expectations, but does not yet commit to one implementation mechanism.
