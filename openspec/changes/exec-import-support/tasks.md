## 1. C# Protocol — harness generation and import validation

- [ ] 1.1 Add `source_path`, `import_base_url`, `reset_jsenv_before_exec` fields to `ExecRequest` in `UnityPuerExecProtocol.cs`
- [ ] 1.2 Remove the `import` rejection regex from `TryRewriteModuleEntry` (lines 102–106 of Protocol.cs)
- [ ] 1.3 Replace `TryBuildWrappedScript` IIFE generation with a harness module string builder: `import __entry from '<entry-specifier>';` plus the existing bridge ceremony as top-level module code
- [ ] 1.4 Add helper `BuildEntrySpecifier(ExecRequest)` that selects the correct entry specifier (real path for `--file`, virtual HTTP entry URL for HTTP base, temp file path for filesystem base)
- [ ] 1.5 Add helper `DetectsImport(string code)` regex that checks for `import` declarations (used to surface `missing_import_base_url` when no base URL is provided)

## 2. C# Server — custom ILoader and ExecuteModule switch

- [ ] 2.1 Implement `PuerExecLoader : ILoader` class in the Editor assembly with a mutable per-request context slot (virtual module map + base URL)
- [ ] 2.2 Implement `FileExists` and `ReadFile` on `PuerExecLoader` per the resolution priority: virtual harness → virtual HTTP entry → HTTP fetch (`WebClient.DownloadString`) → filesystem delegate
- [ ] 2.3 Switch `EnsureJsEnv` to pass a `PuerExecLoader` instance to the `JsEnv` constructor
- [ ] 2.4 In `StartJobEvaluation`: populate the loader's per-request context (register harness and optional virtual entry), call `jsEnv.ExecuteModule("puer-exec://harness/<requestId>")`, clear context after execution
- [ ] 2.5 Add temp file write/cleanup logic for the filesystem-base stdin/code path (write `__puer_exec_entry_<id>.js` to base dir before exec, delete after exec; sweep on next exec if previous cleanup failed)
- [ ] 2.6 Add `/reset-jsenv` HTTP endpoint handler in `UnityPuerExecServer.cs`; handler disposes current `JsEnv` and calls `EnsureJsEnv` to create a fresh one
- [ ] 2.7 Wire `reset_jsenv_before_exec` field: before `StartJobEvaluation`, if flag is set, invoke the reset-jsenv logic inline

## 3. CLI Python — new arguments and payload fields

- [ ] 3.1 Add `--import-base-url` argument to the `exec` subparser in `unity_puer_exec_surface.py`
- [ ] 3.2 Add `--reset-jsenv-before-exec` argument to the `exec` subparser in `unity_puer_exec_surface.py`
- [ ] 3.3 In `run_exec` (runtime), extract `source_path` from `args.file_path` (absolute path via `os.path.abspath`) when `--file` is used; include in payload
- [ ] 3.4 Include `import_base_url` and `reset_jsenv_before_exec` in the exec payload when provided
- [ ] 3.5 Implement the correct before-exec ordering: refresh step first (existing logic), wait for compile if triggered, then invoke `reset-jsenv` endpoint if `--reset-jsenv-before-exec` is set, then exec

## 4. Tests — mocked layer

- [ ] 4.1 Add unit tests for `TryBuildWrappedScript` / harness builder: verify harness imports the correct entry specifier for `--file`, filesystem base, and HTTP base cases
- [ ] 4.2 Add unit tests for `DetectsImport`: confirm regex matches static import declarations and does not fire on string literals or comment-only occurrences
- [ ] 4.3 Add CLI tests for `--import-base-url` argument parsing (accepted, stored in args correctly)
- [ ] 4.4 Add CLI tests for `--reset-jsenv-before-exec` argument parsing
- [ ] 4.5 Add payload construction tests: confirm `source_path` is set from `--file`, `import_base_url` from `--import-base-url`, `reset_jsenv_before_exec` from flag

## 5. Spec archive and meta

- [ ] 5.1 Update `openspec/specs/exec-import-support/spec.md` (move from change dir to specs dir during archive)
- [ ] 5.2 Update `openspec/specs/formal-cli-contract/spec.md` by merging the delta (during archive)
- [ ] 5.3 Update `meta.yaml` for this change as implementation progresses
