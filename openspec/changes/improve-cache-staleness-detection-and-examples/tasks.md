## 1. C# server: mtime tracking and staleness detection

- [ ] 1.1 Add `_sourceFileTimestamps` dictionary field and clear it in `DisposeJsEnv`
- [ ] 1.2 Add `CheckSourceStaleness` method: compare current `File.GetLastWriteTimeUtc` against stored timestamp, return null if ok or an error status string
- [ ] 1.3 Insert staleness check in `HandleExecAsync` before `TryAcceptExecRequest`, returning `module_cache_stale` JSON response when stale
- [ ] 1.4 Handle `FileNotFoundException` in staleness check (treat as not-stale)

## 2. CLI: guidance matrix entry for module_cache_stale

- [ ] 2.1 Add `(exec, module_cache_stale)` entry to `GUIDANCE_MATRIX` with `situation` and `next_steps` including `--reset-jsenv-before-exec` argv template
- [ ] 2.2 Add `file_path` to guidance context in `_build_guidance_context` so argv templates can reference it
- [ ] 2.3 Add `module_cache_stale` to `COMMAND_HELP["exec"]["status"]["failure"]` with exit code and meaning description

## 3. CLI: new `component-detection` help example

- [ ] 3.1 Add `component-detection` entry to `WORKFLOW_EXAMPLES` with script body demonstrating `puer.$typeof(CS.UnityEngine.MeshFilter)`, `puer.$ref()`, `TryGetComponent`, and `get_Item()`
- [ ] 3.2 Add `component-detection` to `WORKFLOW_IDS` list
- [ ] 3.3 Add `component-detection` to `COMMAND_HELP["exec"]["related_workflows"]`

## 4. CLI: PowerShell `$` escape note in --code help

- [ ] 4.1 Add PowerShell single-quote guidance to `COMMAND_HELP["exec"]["args"]["Arguments"]` for the `--code` parameter description

## 5. Validation

- [ ] 5.1 Verify `--help-example component-detection` renders correctly
- [ ] 5.2 Verify `exec --help-status` lists `module_cache_stale`
- [ ] 5.3 Run existing test suite to confirm no regressions
