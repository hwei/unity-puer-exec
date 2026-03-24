## Why

Prompt B still remains `recoverable` rather than `clean` because writing a generated C# editor script forces an import-and-compile cycle before the menu command can be invoked. That recovery is not necessarily a bug, but it is still product-facing workflow friction that the CLI should make easier to complete correctly on the first pass.

## What Changes

- Improve the documented or implemented post-C#-write workflow so Prompt B style runs can move from code write to menu invocation with less recovery guesswork.
- Make the expected compile-recovery step clearer and more deterministic for this workflow.
- Validate the change with a `gpt-5.4-mini subagent` Prompt B rerun that compares whether the workflow still needs the same amount of explicit recovery work.

## Capabilities

### New Capabilities
- None yet; the exact product shape will be decided during implementation.

### Modified Capabilities
- `agent-cli-discoverability-validation`: Prompt B validation can score whether compile-recovery friction moved closer to `clean` rather than merely `recoverable`.

## Impact

- Targets one of the last major Prompt B friction points that remains even after host-log fallback was removed.
- Leaves Prompt B wording unchanged while still demanding transcript-backed evidence of improvement.
- May lead to either a clearer workflow example, a lighter product behavior change, or both.
