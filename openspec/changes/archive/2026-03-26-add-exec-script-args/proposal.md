## Why

`exec` scripts currently need to hardcode per-run values inside the script body, which makes common Unity workflows awkward to reuse across requests and across agents. Now that the public script-entry contract has stabilized around a minimal `ctx` object, this is the right point to add an explicit caller-supplied argument channel without reopening the wrapper-era ambiguity the project already removed.

## What Changes

- Extend `unity-puer-exec exec` with a new `--script-args <text>` option for caller-supplied script arguments.
- Parse `--script-args` as JSON at the CLI boundary and require the top-level value to be an object for the first version.
- Extend the public exec script context so the default-exported entry function receives `ctx.args` alongside `ctx.request_id` and `ctx.globals`.
- Treat accepted exec identity and replay semantics as a combination of script source plus script arguments, so request recovery and request-id conflict detection do not silently reuse mismatched inputs.
- Update pending exec persistence, help text, and examples so `wait-for-exec` recovery preserves script arguments and published authoring guidance documents `ctx.args`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: extend the public exec contract with `--script-args`, `ctx.args`, structured argument validation, and recovery semantics that preserve caller-supplied script arguments.
- `agent-cli-discoverability-validation`: update exec authoring guidance so help-only validation can discover the new script-argument workflow without assuming undocumented runtime behavior.

## Impact

- Affected CLI entrypoints and help surface under `cli/python/`, especially exec argument parsing, pending artifact replay, and authoring examples.
- Affected Unity runtime protocol under `packages/com.txcombo.unity-puer-exec/Editor/`, especially exec request payloads, wrapper construction, and request identity checks.
- Affected unit and real-host validation coverage for exec contract behavior, request replay, and help discoverability.
