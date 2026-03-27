## Why

The repository now publishes `com.txcombo.unity-puer-exec` on OpenUPM, but the most important user path is no longer "local file injection into a prepared host". It is "an agent installs the published package into a real Unity project and then tries to use the package-local CLI". We need a repository-owned validation record for that path, including network and environment friction that a normal agent will hit in practice.

## What Changes

- Record a real-host validation workflow that starts from a clean validation host, installs `com.txcombo.unity-puer-exec` from OpenUPM, waits through package import stabilization, and then verifies a representative package-local CLI workflow.
- Capture the observed outcome of the representative workflow: using the package-local `unity-puer-exec.exe` to perform the `AllBuildWindow` equivalent of "default options plus `BuildBundle`, then Build".
- Distinguish confirmed product behavior from follow-up findings, including transient transport disconnect noise, missing package `.meta` warnings, and OpenUPM download failure on machines that require an HTTP proxy.
- Update the installation/onboarding truth so README prompts and agent guidance can tell the agent to ask for proxy settings when the OpenUPM registry is unreachable instead of failing silently or looping.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `validation-host-integration`: real-host validation truth expands from local package injection to the published OpenUPM install path, including recording external acquisition blockers and the "wait for import stability before exec" boundary.
- `readme-agent-onboarding`: installation guidance changes so agent-facing OpenUPM prompts acknowledge proxy-dependent environments and instruct the agent to ask the user for proxy settings when registry access fails.

## Impact

- [`openspec/specs/validation-host-integration/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/validation-host-integration/spec.md)
- [`openspec/specs/readme-agent-onboarding/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/readme-agent-onboarding/spec.md)
- [`ReadMe.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/ReadMe.md)
- [`ReadMe.zh-CN.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/ReadMe.zh-CN.md)
- Repository-owned validation notes for the published OpenUPM path
