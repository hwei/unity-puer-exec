## Why

When an `exec` entry function returns a Promise (e.g. `export default async function`), the runtime currently treats this identically to a script execution failure: `status:"failed"`, exit code 1, response on stderr. But the function body *has already executed* — `__entry(__ctx)` is called before the thenable check. An agent seeing `failed` reasonably concludes the command didn't run, which is false and can lead to duplicate work or confusion. The runtime needs a distinct state that communicates "your script ran, but the return value could not be captured."

## What Changes

- Introduce a third terminal job status `CompletedWithWarning` in the C# Unity runtime, alongside `Completed` and `Failed`.
- When the harness detects a thenable return value, call `CompleteJobWithWarning` with code `async_result_not_supported` instead of throwing `FailJob`.
- Protocol: Promise returns produce `{"ok":true,"status":"warning","warning":"async_result_not_supported","warning_detail":"..."}` with exit code 0 on stdout.
- Add `CompleteJobWithWarning` bridge method and extend `BuildExecResponseJson` for the new status.
- Update CLI `_status_to_exit_code` to map `warning` → exit 0.
- Reword help text and guidance matrix to distinguish "script body executed, result not captured" from "execution failed."
- Extend `BuildErrorDetailJson` to include human-readable context for `async_result_not_supported` in the response itself.
- Update affected tests.

## Capabilities

### New Capabilities
- `exec-warning-status`: The warning status and protocol for `exec` / `wait-for-exec` responses. Covers the terminal `warning` job state, the JSON shape (`ok:true`, `status:"warning"`, `warning`, `warning_detail`), and CLI exit code mapping.

### Modified Capabilities
- `formal-cli-contract`: The requirement "Promise- or thenable-returning entry functions MUST fail explicitly" changes to "MUST complete with warning." The scenario "Entry function returns a Promise" and the help-text requirement are updated accordingly.
- `runtime-guidance`: The `("exec","failed")` guidance entry is reworded, and a new `("exec","warning")` entry is added.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecJobState.cs` — new enum value, fields, and `CompleteWithWarning` method
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecBridge.cs` — new `CompleteJobWithWarning` bridge entry
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs` — harness JS rewrite, `BuildExecResponseJson` new branch, `BuildErrorDetailJson` extension
- `cli/python/direct_exec_client.py` — exit code mapping for `warning`
- `cli/python/help_surface.py` — help text + guidance matrix entries
- `tests/test_unity_session_cli.py` — assertion text update
- `tests/test_real_host_integration.py` — status assertion change
- `tests/test_package_layout.py` — verify `async_result_not_supported` still present
