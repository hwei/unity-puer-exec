## Why

Current agent-validation evidence now points to a distinct discoverability gap around the JavaScript-to-C# bridge shape used by `unity-puer-exec`. In both Prompt A and Standard Prompt C, medium-capability agents spend extra steps probing how JavaScript is expected to access Unity and C# APIs before they can focus on the actual task. The current help surface exposes this mostly through examples such as `puer.loadType(...)`, but it does not yet make the bridge model explicit enough to be quickly recognized as a PuerTS-style workflow. One concrete sub-problem is bridged collection semantics: C# arrays and generic lists do not behave like ordinary JavaScript arrays, yet the current help surface does not warn callers about that difference.

This should be tracked independently from compile-recovery and log-observation issues so the repository can decide whether to improve help wording, examples, terminology, or external reference links without conflating that work with runtime behavior changes.

## What Changes

- Update the published CLI help surface so it explicitly frames `unity-puer-exec` script authoring as a PuerTS-style JavaScript-to-C# bridge workflow.
- Add a concise bridge mental-model explanation to the help surface so callers can recognize `puer.loadType(...)` and related bridged-type usage without first inferring the model from incidental examples.
- Add a short warning that bridged C# arrays and `List<T>` values are not plain JavaScript arrays.
- Add or revise a help example so bridge usage is discoverable through a purpose-built help path instead of only through the editor-exit example.
- Attach an official PuerTS JS-to-C# reference link as a supplement to repository-owned help text.
- Update validation expectations so future reruns can measure whether the revised help surface reduces bridge-shape probing.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: help and guidance around JavaScript-to-C# bridge usage may need to become more explicit for agent callers.
- `agent-cli-discoverability-validation`: baseline validation may need targeted evidence for whether agents quickly discover the intended PuerTS-style bridge usage.

## Impact

- Affects CLI help, examples, and bridge-oriented guidance rather than runtime execution behavior.
- Helps separate bridge discoverability issues from compile workflow and log-observation workflow issues.
- Intentionally limits scope to help and validation guidance; it does not add a new runtime command or bridge wrapper API.
