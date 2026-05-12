## 1. Unity server — CompilationPipeline hooks

- [x] 1.1 Add `CompilationPipeline.compilationStarted` subscriber that resets error/warning counters, message collections, and `_lastCompilationHadErrors` flag
- [x] 1.2 Add `CompilationPipeline.assemblyCompilationFinished` subscriber that collects `CompilerMessage[]` entries, splits by type (Error/Warning), increments counters, and sets `_lastCompilationHadErrors` when errors are present
- [x] 1.3 Declare thread-safe fields: `_lastCompilationHadErrors` (volatile bool), counters (int with Interlocked), message lists with lock

## 2. Unity server — new HTTP endpoints

- [x] 2.1 Add `GetCompileErrorsRequest` and `GetCompileWarningsRequest` serializable classes in `UnityPuerExecProtocol.cs`
- [x] 2.2 Implement `/get-compile-errors` endpoint: accepts `start` (default 0) and `count` (default 3, max 100), returns `{total, returned, messages}`
- [x] 2.3 Implement `/get-compile-warnings` endpoint: same signature, returns warnings
- [x] 2.4 Wire endpoints into `HandleContextAsync` routing

## 3. Unity server — exec and wait-for-exec gate

- [x] 3.1 Add `_lastCompilationHadErrors` check in `HandleExecAsync`, after the `IsCompilingOrReloading()` check and before request parsing. Return `BuildSimpleErrorJson("unity_compile_error", ...)` with inline compile diagnostics
- [x] 3.2 Add same check in `HandleWaitForExecAsync` before the existing request-id lookup
- [x] 3.3 Build the inline response payload: `compile_errors_total`, `compile_warnings_total`, and `compile_messages` (up to 3, errors first). Each message includes `type`, `message`, `file`, `line`, `column`
- [x] 3.4 Ensure `/health` still returns `ready` when compile errors exist (health is about editor reachability, not compilation state)

## 4. CLI — exit code and status mapping

- [x] 4.1 Add `EXIT_UNITY_COMPILE_ERROR = 23` in `direct_exec_client.py`
- [x] 4.2 Add `"unity_compile_error"` case in `_status_to_exit_code` returning `EXIT_UNITY_COMPILE_ERROR`
- [x] 4.3 Add `EXIT_UNITY_COMPILE_ERROR` to the handled-exit-codes tuple in `invoke_command`

## 5. CLI — new commands

- [x] 5.1 Add `get-compile-errors` subparser in `unity_puer_exec_surface.py` with `--project-path`/`--base-url` selectors, `--start` (int, default 0), `--count` (int, default 3)
- [x] 5.2 Add `get-compile-warnings` subparser in `unity_puer_exec_surface.py` with same arguments
- [x] 5.3 Implement `run_get_compile_errors` in `unity_puer_exec_runtime.py`: validate start >= 0, count in [1, 100], resolve selector, post to `/get-compile-errors`, return result
- [x] 5.4 Implement `run_get_compile_warnings` in `unity_puer_exec_runtime.py`: same flow, post to `/get-compile-warnings`
- [x] 5.5 Wire new commands into `run_command` dispatch

## 6. CLI — exec response handling

- [x] 6.1 In `run_exec` and `run_wait_for_exec`, recognize `unity_compile_error` as a terminal status (not remapped to `running`), preserve the inline compile diagnostics in the response
- [x] 6.2 Ensure `unity_compile_error` is handled in `_normalize_exec_response` and `_normalize_exec_lifecycle_body` as a terminal, non-running status

## 7. CLI — runtime guidance

- [x] 7.1 Add `(exec, unity_compile_error)` entry in `GUIDANCE_MATRIX` in `help_surface.py` with `situation` text referencing compile error/warning counts and `next_steps` candidates
- [x] 7.2 The primary `next_steps` candidate SHALL be `exec` with `--refresh-before-exec` and a concrete `argv` template
- [x] 7.3 Add secondary `next_steps` candidate for `get-compile-errors`
- [x] 7.4 Add `(wait-for-exec, unity_compile_error)` entry with corresponding guidance
- [x] 7.5 Add `unity_compile_error` to exec and wait-for-exec `--help-status` output in `COMMAND_HELP`

## 8. Validation

- [x] 8.1 Add test case in `test_direct_exec_client.py` for `EXIT_UNITY_COMPILE_ERROR` exit code and status mapping
- [x] 8.2 Add test case in `test_unity_session_cli.py` for `get-compile-errors` and `get-compile-warnings` argument validation (negative start, out-of-range count)
- [x] 8.3 Add guidance matrix test verifying `(exec, unity_compile_error)` produces `situation` and `next_steps` with `--refresh-before-exec` argv
- [x] 8.4 Real-host integration smoke test: introduce a deliberate C# compile error, invoke exec, verify `unity_compile_error` status and inline messages (manual or `.tmp/` probe)
