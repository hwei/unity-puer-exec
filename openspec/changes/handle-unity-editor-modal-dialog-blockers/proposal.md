## Why

Real Unity Editor workflows can surface native modal dialogs such as unsaved-scene save prompts. Today those dialogs can block `unity-puer-exec` progress invisibly, leaving the CLI to stall until a human clicks through, which is neither machine-usable nor validation-friendly.

## What Changes

- Define product expectations for detecting or surfacing Unity Editor modal dialog blockers during project-scoped workflows.
- Define validation expectations for reproducing and observing modal-dialog blocking behavior against the real host.
- Scope a follow-up implementation path that prefers machine-usable blocker reporting over silent timeout-driven stalls.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: project-scoped workflows should surface modal dialog blockers as machine-usable blocking states or diagnostics instead of relying on silent hangs.
- `validation-host-integration`: real-host validation should cover at least one modal-dialog blocker scenario and record the observable blocker outcome.

## Impact

- Affects project-scoped readiness and execution flows in the Python CLI/session layer.
- Affects real-host validation workflows and discoverability regression interpretation.
- May later require Unity-side or host-observation support, but this change is primarily about contract and implementation planning.
