## Why

The Prompt B probe showed that the observed `ctx` contract was narrower than a task author might reasonably assume. In that run, `ctx` exposed `request_id` and `globals`, but not `project_path`. A user who assumes undocumented fields exist can get a misleadingly successful first step followed by missing host-side effects.

## What Changes

- Publish a clearer contract for the script `ctx` object, including which fields are guaranteed and which are not promised.
- Add guidance for deriving project-local paths through Unity APIs when the script needs them.
- Validate the change with a `gpt-5.4-mini subagent` Prompt B rerun that checks whether task scripts still assume unsupported `ctx` fields.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: Prompt B reruns can measure whether script-context misunderstandings decrease after the contract is clarified.

## Impact

- Reduces ambiguity around the runtime script context passed into `exec`.
- Makes file-writing and cleanup scripts more predictable for agent-generated workflows.
- Produces Prompt B evidence about whether context-contract clarification removes a concrete first-pass failure mode.
