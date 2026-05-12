## Context

The Unity Editor's `EditorApplication.isCompiling` only signals that compilation is *in progress*. Once compilation finishes — whether successfully or with errors — the flag resets to false. The `/health` endpoint returns `ready`, and `exec` proceeds to run JavaScript against whatever C# types are (or aren't) available. C# compilation errors are invisible to the agent.

The existing `compiling` status and `--refresh-before-exec` flag provide partial coverage: `compiling` gates during active compilation, and `--refresh-before-exec` triggers `AssetDatabase.Refresh()` to force recompilation. But there is no signal for the case where compilation *finished with errors*.

## Goals / Non-Goals

**Goals:**
- Detect C# compilation errors via Unity's `CompilationPipeline` API
- Return a distinct `unity_compile_error` status from `/exec` and `/wait-for-exec` when the last compilation had errors
- Include inline error/warning counts and up to 3 messages (errors prioritized) in the exec response
- Provide dedicated endpoints and CLI commands for ranged retrieval of full error/warning lists
- Include machine-usable guidance that tells the agent to fix C# and re-run with `--refresh-before-exec`
- Keep the detection scoped to the current compilation session (reset on `compilationStarted`)

**Non-Goals:**
- Parsing compile errors from Editor.log (fragile, async, log-format-dependent)
- Detecting compilation errors from CI/build pipelines (Editor-only scope)
- Auto-triggering compilation when `exec` detects changed `.cs` files (existing `--refresh-before-exec` already serves this)
- Tracking per-file staleness beyond the existing `module_cache_stale` mechanism

## Decisions

### Detection: CompilationPipeline hooks

Use `CompilationPipeline.compilationStarted` and `CompilationPipeline.assemblyCompilationFinished` rather than log parsing or polling.

- `compilationStarted`: reset all counters and message buffers. This ensures errors from a previous compilation session don't leak into the current one.
- `assemblyCompilationFinished(string assembly, CompilerMessage[] messages)`: iterate messages, split by `type` (Error vs Warning), increment counters, append to thread-safe collections.

**Alternatives considered:**
- Pollling `EditorApplication.isCompiling` + log tailing: fragile, timing-dependent, requires log format parsing.
- `AssemblyReloadEvents`: fires after *successful* compilation only; no error detail available.

### Error gate placement: exec endpoint, not health

The `/health` endpoint answers "is the editor reachable and ready for interaction." With compile errors, the editor is still reachable — log inspection, blocker detection, and other non-exec operations should still work. Returning a non-ready health status would block those operations.

Instead, the gate lives in `HandleExecAsync`, after the existing `IsCompilingOrReloading()` check. If `_lastCompilationHadErrors` is true, return `unity_compile_error` instead of proceeding to JS execution.

### Inline message cap: 3 total, errors first

The exec response includes inline compile messages to give the agent immediate context without a separate round-trip. The cap is 3 messages total (errors + warnings combined), with errors taking priority slots. Remaining messages require `get-compile-errors` / `get-compile-warnings`.

This keeps the exec response compact while still providing actionable context. Most compilation errors cluster around a root cause; the first few messages usually identify the problem.

### Ranged retrieval endpoints

`/get-compile-errors?start=0&count=10` and `/get-compile-warnings?start=0&count=10` support paginated retrieval. This follows the existing pattern of the `get-log-briefs` command. Default count is 3, max count is 100.

### Reset strategy: on compilation start

Reset all state (`_lastCompilationHadErrors`, counters, message buffers) when `compilationStarted` fires. This is cleaner than resetting on successful compilation or on exec, because:
- Different compilations are different sessions — errors from the previous one shouldn't persist
- If the agent fixes C# and Unity recompiles, the flag auto-clears
- No need to track timestamps or compare session markers

### CLI guidance: follow existing GUIDANCE_MATRIX pattern

Add `(exec, unity_compile_error)` and `(wait-for-exec, unity_compile_error)` entries to the guidance matrix. Each includes `situation` text and `next_steps` with concrete `argv` templates that include `--refresh-before-exec`.

## Risks / Trade-offs

- **Unity version compatibility**: `CompilationPipeline` is available since Unity 2018.1. The existing minimum Unity version for this package supports it.
- **Assembly reload during compilation**: `compilationStarted` fires before assembly reload, `assemblyCompilationFinished` fires after. The server is stopped during reload (via `AssemblyReloadEvents.beforeAssemblyReload`). The static fields survive reload (they're reinitialized in the static constructor on `[InitializeOnLoad]`). This is fine: a successful compilation triggers reload, which restarts the server with fresh state.
- **Multiple assemblies with mixed results**: If assembly A compiles with errors but assembly B compiles clean, `_lastCompilationHadErrors` is still true. The agent sees the errors from A and fixes them. On recompilation, the flag resets. This is the correct behavior — partial success is still failure from the agent's perspective.
- **Message collection thread safety**: `assemblyCompilationFinished` fires on the main thread (like most Editor callbacks), so no concurrency issue. But we use `lock` on the message lists defensively in case Unity changes this.
