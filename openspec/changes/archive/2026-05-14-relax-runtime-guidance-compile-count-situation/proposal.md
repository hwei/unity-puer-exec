## Why

The runtime-guidance spec currently requires `unity_compile_error` situation text to repeat the exact compile error and warning counts from the response. That requirement conflicts with the existing static guidance-matrix design, while the structured count fields already provide the machine-readable detail.

## What Changes

- Relax the `exec unity_compile_error` guidance requirement so `situation` points callers to structured compile diagnostic fields instead of embedding dynamic counts in prose.
- Preserve the requirement that the response explains the compile-error condition, states that the script was not executed, and guides callers to fix C# errors and recompile.
- No runtime behavior or CLI API changes are required.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-guidance`: Relax the `unity_compile_error` situation wording requirement to align with static guidance-matrix behavior.

## Impact

- Affects OpenSpec durable requirements only.
- No code, package API, CLI output schema, or dependency changes.
