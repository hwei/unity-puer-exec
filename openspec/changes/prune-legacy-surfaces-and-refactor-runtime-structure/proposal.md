## Why

The repository-level layout is still healthy, but the runtime implementation has started to accumulate transitional surfaces and oversized orchestration files. That increases change cost, makes compatibility decisions ambiguous, and risks carrying migration scaffolding forward as if it were formal product surface.

## What Changes

- Remove repository-owned runtime code that is demonstrably unused transitional scaffolding.
- Reclassify compatibility-only entry points and helpers as isolated shims instead of normal extension points.
- Refactor the Python CLI/session runtime into smaller modules with clearer ownership boundaries.
- Refactor the Unity Editor runtime so HTTP serving, job state, bridge helpers, and script-wrapping logic no longer live in one monolithic file.
- Preserve the formal `unity-puer-exec` command contract and real-host validation behavior while reducing internal structural complexity.

## Capabilities

### New Capabilities
- `runtime-structure-hygiene`: define durable structural rules for isolating compatibility shims, pruning confirmed-dead scaffolding, and keeping runtime modules aligned to explicit responsibilities.

### Modified Capabilities
- `formal-cli-contract`: tighten the compatibility-path requirement so transitional aliases remain thin shims and do not accumulate new authoritative behavior.

## Impact

- Affected Python runtime: `cli/python/unity_puer_exec.py`, `cli/python/unity_session.py`, `cli/python/unity_puer_session.py`, `cli/python/help_surface.py`
- Affected Unity runtime: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`
- Affected tests: CLI contract tests, runtime unit tests, and package-layout assertions
- Affected repository truth: change-local specs for CLI compatibility posture and runtime structure hygiene
