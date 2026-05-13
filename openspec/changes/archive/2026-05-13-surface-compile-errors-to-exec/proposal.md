## Why

When the Unity Editor has C# compilation errors, the agent has no way to know. The current `compiling` status only fires while the compiler is *active*; once compilation finishes (with or without errors), both `/health` and `/exec` proceed as if everything is fine. The agent runs JavaScript against a broken or stale C# type system, getting confusing failures or silently wrong results.

## What Changes

- The Unity server subscribes to `CompilationPipeline` to track compile errors and warnings per compilation session
- `/exec` and `/wait-for-exec` return a new `unity_compile_error` status when the last compilation had errors, including inline error/warning counts and up to 3 messages (errors first)
- New HTTP endpoints `/get-compile-errors` and `/get-compile-warnings` support ranged retrieval of full diagnostic messages
- CLI adds exit code 23 (`EXIT_UNITY_COMPILE_ERROR`) and two new commands: `get-compile-errors` and `get-compile-warnings`
- Runtime guidance entries for `unity_compile_error` tell the agent to fix C# errors and re-run with `--refresh-before-exec`

## Capabilities

### New Capabilities
- `compile-error-surface`: Detect C# compilation errors and warnings in the Unity Editor via `CompilationPipeline` hooks, and surface them through exec responses and dedicated CLI diagnostic commands.

### Modified Capabilities
- `runtime-guidance`: New `(exec, unity_compile_error)` and `(wait-for-exec, unity_compile_error)` guidance entries with situation text and next-steps templates.
- `formal-cli-contract`: New exit code 23, new `get-compile-errors` and `get-compile-warnings` commands with their argument contracts and status semantics.

## Impact

- **Unity package**: `UnityPuerExecServer.cs` (CompilationPipeline hooks, new endpoints, exec gate), `UnityPuerExecProtocol.cs` (response/request types)
- **CLI**: `direct_exec_client.py` (exit code, status mapping), `unity_puer_exec_runtime.py` (new command handlers, exec response handling), `unity_puer_exec_surface.py` (new subcommands), `help_surface.py` (guidance entries)
- **No breaking changes**: existing commands, exit codes, and response formats are unchanged
