## Why

Current agent-validation evidence now points to a distinct discoverability gap around the JavaScript-to-C# bridge shape used by `unity-puer-exec`. In both Prompt A and Standard Prompt C, medium-capability agents spend extra steps probing how JavaScript is expected to access Unity and C# APIs before they can focus on the actual task. The current help surface exposes this mostly through examples such as `puer.loadType(...)`, but it does not yet make the bridge model explicit enough to be quickly recognized as a PuerTS-style workflow.

This should be tracked independently from compile-recovery and log-observation issues so the repository can decide whether to improve help wording, examples, terminology, or external reference links without conflating that work with runtime behavior changes.

## What Changes

- Explore how the current CLI help surface communicates the JavaScript-to-C# bridge model and where agents are still forced into bridge-shape probing.
- Define the high-level improvement goal for making the PuerTS-style bridge discoverable faster to agent callers.
- Capture candidate guidance improvements such as terminology, dedicated help sections, examples, or an official reference link, without committing to a specific implementation yet.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: help and guidance around JavaScript-to-C# bridge usage may need to become more explicit for agent callers.
- `agent-cli-discoverability-validation`: baseline validation may need targeted evidence for whether agents quickly discover the intended PuerTS-style bridge usage.

## Impact

- Affects CLI help, examples, and bridge-oriented guidance rather than runtime execution behavior.
- Helps separate bridge discoverability issues from compile workflow and log-observation workflow issues.
- This change is intentionally exploration-first and does not yet commit to code changes.
