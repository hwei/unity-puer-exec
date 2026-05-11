## 1. C# server: mtime tracking and staleness detection

- [x] 1.1 Add `_sourceFileTimestamps` dictionary field and clear it in `DisposeJsEnv`
- [x] 1.2 Add `CheckSourceStaleness` method: compare current `File.GetLastWriteTimeUtc` against stored timestamp, return null if ok or an error status string
- [x] 1.3 Insert staleness check in `HandleExecAsync` before `TryAcceptExecRequest`, returning `module_cache_stale` JSON response when stale
- [x] 1.4 Handle `FileNotFoundException` in staleness check (treat as not-stale)

## 2. CLI: guidance matrix entry for module_cache_stale

- [x] 2.1 Add `(exec, module_cache_stale)` entry to `GUIDANCE_MATRIX` with `situation` and `next_steps` including `--reset-jsenv-before-exec` argv template
- [x] 2.2 Add `file_path` to guidance context in `_build_guidance_context` so argv templates can reference it
- [x] 2.3 Add `module_cache_stale` to `COMMAND_HELP["exec"]["status"]["failure"]` with exit code and meaning description

## 3. CLI: new `component-detection` help example

- [x] 3.1 Add `component-detection` entry to `WORKFLOW_EXAMPLES` with script body demonstrating `puer.$typeof(CS.UnityEngine.MeshFilter)`, `puer.$ref()`, `TryGetComponent`, and `get_Item()`
- [x] 3.2 Add `component-detection` to `WORKFLOW_IDS` list
- [x] 3.3 Add `component-detection` to `COMMAND_HELP["exec"]["related_workflows"]`

## 4. CLI: PowerShell `$` escape note in --code help

- [x] 4.1 Add PowerShell single-quote guidance to `COMMAND_HELP["exec"]["args"]["Arguments"]` for the `--code` parameter description

## 5. Validation

- [x] 5.1 Verify `--help-example component-detection` renders correctly
- [x] 5.2 Verify `exec --help-status` lists `module_cache_stale`
- [x] 5.3 Run existing test suite to confirm no regressions (pytest not available; Python import verification passed, help rendering verified)
