## Why

When users modify a `.js` file and re-run `exec --file`, PuerTS's internal module cache silently returns the old compiled code. The only existing workaround (`--reset-jsenv-before-exec`) destroys the entire JsEnv and is not obvious to users. This causes wasted debugging time chasing phantom errors from stale code. Additionally, the help examples lack coverage for the most common scene-inspection patterns (component detection with `$typeof`/`$ref`/`TryGetComponent`), forcing users to discover PuerTS bridge pitfalls through trial and error.

## What Changes

- **C# server tracks `source_path` mtime** and returns a new `module_cache_stale` error when a previously-executed file has been modified, instead of silently running cached code.
- **CLI surfaces `module_cache_stale`** with actionable guidance in the error response and `next_steps`/`situation` fields, directing users to `--reset-jsenv-before-exec` or file renaming.
- **New `--help-example` entry** for component detection: the standard `puer.$typeof(CS.UnityEngine.X)` + `puer.$ref()` + `TryGetComponent` + `get_Item()` pattern.
- **PowerShell `$` escape note** added to `--code` parameter help text.

## Capabilities

### New Capabilities
- `cache-staleness-detection`: C# server detects when a `--file` source file has been modified since its last execution and returns a machine-readable error instead of executing stale cached code. The CLI surfaces this error with actionable guidance.

### Modified Capabilities
- `exec-import-support`: Extend the existing `--reset-jsenv-before-exec` requirement to reference staleness detection as the complementary detection mechanism — staleness is detected first, and `--reset-jsenv-before-exec` is the prescribed resolution.
- `formal-cli-contract`: Add `module_cache_stale` as a new documented error status for `exec`. Extend help requirements to cover the component-detection example and PowerShell `$` escape note.

## Impact

- **C#**: `UnityPuerExecServer.cs` — new mtime tracking dictionary and staleness check in the exec request path.
- **Python CLI**: `unity_puer_exec_runtime.py` — guidance matrix entry for `module_cache_stale` status; `help_surface.py` — new example and `--code` help text update.
- **Specs**: `exec-import-support/spec.md` and `formal-cli-contract/spec.md` get delta updates.
- No breaking changes to the HTTP protocol or CLI surface.
