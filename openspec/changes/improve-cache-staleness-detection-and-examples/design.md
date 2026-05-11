## Context

PuerTS's `JsEnv` maintains an internal module cache keyed by module specifier. When `exec --file` sends the same file path twice, PuerTS returns the cached compiled module without re-reading the file. The existing escape hatch (`--reset-jsenv-before-exec`) destroys and recreates the entire `JsEnv`, which clears all caches but is heavyweight, slow, and undiscoverable.

User feedback from real-world scene-analysis scripting confirms this is the #1 friction point: modified code silently runs as its old version, causing users to debug phantom errors from stale line numbers and stale code.

The current `exec` request flow is:

```
HandleExecAsync
  ├─ TryAcceptExecRequest (idempotency check)
  ├─ Main thread enqueue
  │   ├─ [if reset_jsenv_before_exec] ResetJsEnv()
  │   └─ StartJobEvaluation
  │       └─ jsEnv.ExecuteModule(specifier)  ← PuerTS cache may return stale module
  └─ WaitForTerminalOrTimeoutAsync
```

## Goals / Non-Goals

**Goals:**
- Detect when a `--file` source has been modified since its last execution and return a clear, machine-readable error instead of silently running stale code.
- Surface actionable CLI guidance telling the user to use `--reset-jsenv-before-exec` or rename the file.
- Clear the mtime tracking state when JsEnv is reset, so the next execution proceeds normally.
- Add a `--help-example` for component detection covering `puer.$typeof(CS.XXX)`, `puer.$ref()`, `TryGetComponent`, and `get_Item()`.
- Add a PowerShell `$` escape note to the `--code` argument help text.

**Non-Goals:**
- Per-module cache eviction from PuerTS (not supported by the PuerTS API).
- Auto-invalidation or auto-reset of the JsEnv when staleness is detected (the user chooses the remedy).
- File content hashing (mtime is sufficient and simpler).
- Cache invalidation for `--code` or `--stdin` mode (no file path to track).

## Decisions

### 1. C# server tracks `source_path` → last mtime, rejects before job creation

The staleness check happens **before** `TryAcceptExecRequest` in `HandleExecAsync`, so it does not consume a request slot or interact with the idempotency model. A stale file is rejected immediately.

```
HandleExecAsync
  ├─ [NEW] CheckSourceStaleness(request.source_path)
  │   └─ if stale → return {"ok":false, "status":"module_cache_stale", ...}
  ├─ TryAcceptExecRequest (unchanged)
  └─ ...
```

**State**: A `Dictionary<string, DateTime> _sourceFileTimestamps` maps absolute `source_path` to the `File.GetLastWriteTimeUtc` seen at last successful execution start. Cleared on `ResetJsEnv()`.

**Rationale**: Placing the check before `TryAcceptExecRequest` means a stale-file request never becomes an active job, never consumes `activeRequestId`, and never needs a `request_id_conflict` resolution. It is a pre-flight rejection.

**Alternative considered**: Check inside `StartJobEvaluation` after job creation. Rejected because it would require cleaning up job state and would produce confusing `busy`/conflict interactions.

### 2. The error status is `module_cache_stale`, not a generic `failed`

A new top-level status `module_cache_stale` is returned. This lets the CLI guidance matrix provide tailored `next_steps` with concrete `argv` for `--reset-jsenv-before-exec`.

**Response shape** (C# side via `BuildSimpleErrorJson` variant):
```json
{
  "ok": false,
  "status": "module_cache_stale",
  "request_id": "<request_id>",
  "error": "source file has been modified since last execution; use --reset-jsenv-before-exec or rename the file"
}
```

**Alternative considered**: Return `failed` with `error = "module_cache_stale"`. Rejected because the guidance matrix keys on `(command, status)` and cannot branch on error subtype within `failed`.

### 3. CLI guidance matrix entry for `(exec, module_cache_stale)`

Added to `GUIDANCE_MATRIX` in `help_surface.py`:

```python
("exec", "module_cache_stale"): {
    "situation": "The source file has been modified since its last execution but PuerTS module cache still holds the old version. The script was not executed.",
    "next_steps": [
        {
            "command": "exec",
            "when": "re-run with --reset-jsenv-before-exec to clear the module cache",
            "argv_template": [
                "unity-puer-exec", "exec",
                "--project-path", "{project_path}",
                "--file", "{file_path}",
                "--reset-jsenv-before-exec",
            ],
        },
        {
            "command": "exec",
            "when": "rename the script file (e.g., script_v2.js) and exec with the new filename to bypass the cache",
        },
    ],
},
```

The `{file_path}` context variable is added to `_build_guidance_context` so `argv` can be fully constructed.

### 4. Mtime tracking is cleared on JsEnv reset

`ResetJsEnv()` and `DisposeJsEnv()` clear `_sourceFileTimestamps`. When the user follows the guidance and re-runs with `--reset-jsenv-before-exec`, the stale detection is naturally reset.

### 5. New help example: `component-detection`

Added to `WORKFLOW_EXAMPLES` in `help_surface.py` with id `component-detection`. Covers:

- `puer.$typeof(CS.UnityEngine.X)` for type loading (more reliable than `puer.loadType`)
- `puer.$ref()` for out-parameter references
- `TryGetComponent(type, outRef)` for component detection
- `get_Item(i)` for C# indexer access
- Context that this is the recommended pattern for scene inspection scripts

### 6. PowerShell `$` note in `--code` help text

Added to `exec` command args help in `COMMAND_HELP["exec"]["args"]`: a note that PowerShell users should use single quotes (`'...'`) around `--code` values containing `$` to prevent variable expansion, or use `--file` instead.

## Risks / Trade-offs

- **mtime precision across file systems**: FAT32 has 2-second resolution; NTFS has 100ns. If a user saves twice within the FAT32 resolution window, staleness won't be detected. → Mitigation: Acceptable — rapid re-saves in <2s are rare in practice and `--reset-jsenv-before-exec` remains available as an explicit override.

- **File deleted between exec calls**: `File.GetLastWriteTimeUtc` throws `FileNotFoundException`. → Mitigation: Catch the exception and treat as "not stale" — the file is new to us.

- **Clock changes (DST, manual clock adjustment)**: Could cause false positives or negatives. → Mitigation: Use UTC timestamps. False positive (detected as stale when unchanged) is safe — it just asks the user to add `--reset-jsenv-before-exec`. False negative requires a >1h clock shift combined with a file save within that window, which is extremely unlikely.
