## Why

The `exec` command currently evaluates JS scripts in V8 script context, which does not support `import` statements. This prevents users from building reusable JS libraries and composing exec scripts from multiple modules. Lifting this constraint unlocks a meaningful extension pattern for users without requiring any product-side package management.

## What Changes

- The exec command switches from `jsEnv.Eval()` (script context) to `jsEnv.ExecuteModule()` (ES module context) using PuerTS 3.0's ILoader interface.
- A custom `ILoader` is introduced that resolves virtual module specifiers (`puer-exec://harness/<id>`), filesystem paths, and HTTP URLs.
- A bridge harness module is generated per-request, replacing the current inline IIFE wrapping. The user's entry file is imported by the harness rather than inlined.
- New CLI parameter `--import-base-url <url-or-path>` sets the import resolution base (filesystem directory or HTTP URL).
- For `--file` mode, `source_path` (absolute path) is automatically extracted and sent in the payload so relative imports resolve correctly.
- For `--code`/`--stdin` mode, `import` without `--import-base-url` results in a clear `missing_import_base_url` error.
- New CLI parameter `--reset-jsenv-before-exec` resets the JsEnv singleton before executing, clearing the module cache (useful when JS library files change without C# recompilation).
- Execution order when multiple before-exec flags are combined: `refresh → wait for compile → reset JsEnv → exec`.
- New HTTP endpoint `reset-jsenv` on the Unity server side (also used internally by the CLI flag).
- ExecRequest protocol gains three optional fields: `source_path`, `import_base_url`, `reset_jsenv_before_exec`.
- Static `import` in scripts is now a supported contract; the previous `invalid_exec_module` rejection for import statements is removed.

## Capabilities

### New Capabilities

- `exec-import-support`: Rules governing how exec scripts resolve ES module imports — entry specifier selection, ILoader resolution priority (virtual harness, virtual HTTP entry, HTTP fetch, filesystem fallback), `--import-base-url` semantics, `--reset-jsenv-before-exec` semantics, and error behavior when import is used without a base URL.

### Modified Capabilities

- `formal-cli-contract`: The `exec` command surface gains new arguments (`--import-base-url`, `--reset-jsenv-before-exec`) and the protocol payload gains new optional fields (`source_path`, `import_base_url`, `reset_jsenv_before_exec`). Static `import` in exec scripts changes from an error to a supported feature.

## Impact

- **`packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs`**: Remove import rejection; rewrite `TryBuildWrappedScript` to generate harness module string.
- **`packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`**: Introduce custom `ILoader`; switch `StartJobEvaluation` to `ExecuteModule`; add `reset-jsenv` endpoint; update `JsEnv` initialization.
- **`cli/python/unity_puer_exec_surface.py`**: Add `--import-base-url` and `--reset-jsenv-before-exec` arguments to `exec` parser.
- **`cli/python/unity_puer_exec_runtime.py`**: Extract `source_path` from `--file` arg; include new fields in exec payload; handle reset-jsenv flow and execution ordering.
- **`openspec/specs/formal-cli-contract/spec.md`**: Delta for new exec arguments and protocol fields.
- No breaking changes to existing exec scripts that do not use `import`.
