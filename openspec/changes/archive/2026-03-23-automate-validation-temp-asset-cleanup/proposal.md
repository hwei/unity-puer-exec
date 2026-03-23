## Why

Recent host-validation reruns left temporary C# files and scene assets in the external Unity validation project. That residue makes later validation runs noisier and weakens confidence that a result came from the current trial rather than a prior leftover artifact.

## What Changes

- Add a harness-owned cleanup workflow for validation-created temporary Unity assets after rerun tasks complete.
- Define a stable inventory of temporary asset locations and naming conventions that the harness may remove without relying on subagent-authored cleanup.
- Require cleanup to run for both success and failure paths, with durable reporting of what was removed or what residue remains.
- Keep cleanup responsibility out of subagent task prompts so validation measures product workflow rather than agent diligence about teardown.

## Capabilities

### New Capabilities
- `validation-temp-asset-cleanup`: harness-managed cleanup of temporary validation assets in the host Unity project after rerun workflows

### Modified Capabilities
- `agent-cli-discoverability-validation`: validation reruns must report host-project cleanup status and should not leave temporary validation assets behind as normal steady-state behavior

## Impact

- Affected systems: validation rerun workflow, host-project cleanup probes, and any helper scripts that create temporary C# files or scenes for validation.
- Likely code areas: validation harness scripts, `.tmp/` probes that seed host assets, and rerun documentation or result-writing utilities.
- No intended product API change for `unity-puer-exec`; this is a workflow and harness tightening change.
