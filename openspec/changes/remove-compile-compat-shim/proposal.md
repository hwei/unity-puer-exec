## Why

The Unity package still ships `UnityPuerExecCompileCompat.cs`, a transitional compile-trigger shim that was intentionally isolated during the March 18 runtime cleanup and left for later confirmation. Repository inspection now shows no remaining repository callers, no authoritative README or CLI contract dependency, and no active product workflow that depends on the shim instead of the formal `exec --refresh-before-exec` path.

Keeping the file in the package now preserves historical residue rather than product behavior. Removing it aligns the package with the existing runtime-structure hygiene rules and eliminates a dead Editor surface before it leaks into future maintenance or external assumptions.

## What Changes

- Remove the Unity package's `UnityPuerExecCompileCompat.cs` shim and its package metadata file.
- Remove the package-layout assertions that still require the compile-compat shim to exist.
- Reconfirm that the formal refresh workflow remains `exec --refresh-before-exec` and that no documentation or tests treat the shim as an authoritative runtime surface.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `runtime-structure-hygiene`: clarify that an isolated compatibility shim must be deleted once later repository inspection confirms it has no remaining callers, formal documentation dependency, or required validation role.

## Impact

- Affected Unity package files under `packages/com.txcombo.unity-puer-exec/Editor/`.
- Affected package-layout tests in `tests/test_package_layout.py`.
- Affected durable governance for runtime cleanup decisions in `openspec/specs/runtime-structure-hygiene/`.
