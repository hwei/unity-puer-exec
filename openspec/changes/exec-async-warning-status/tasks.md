## 1. C# Runtime: Job state model

- [ ] 1.1 Add `CompletedWithWarning` value to `UnityPuerExecJobStatus` enum in `UnityPuerExecJobState.cs`
- [ ] 1.2 Add `WarningCode` and `WarningDetail` fields to `UnityPuerExecJobSnapshot` struct
- [ ] 1.3 Add `CompleteWithWarning(string warningCode, string warningDetail)` method to `UnityPuerExecJob` class, mirroring `Complete` / `Fail` patterns

## 2. C# Runtime: Bridge entry

- [ ] 2.1 Add `CompleteJobWithWarning(string jobId, string warningCode, string warningDetail)` static method to `UnityPuerExecBridge`, calling `UnityPuerExecServer.CompleteJobWithWarning`
- [ ] 2.2 Add `CompleteJobWithWarning` static method to `UnityPuerExecServer`, calling `job.CompleteWithWarning` and `ReleaseActiveRequest`

## 3. C# Runtime: Protocol and harness

- [ ] 3.1 In `UnityPuerExecProtocol.BuildExecResponseJson`, add `CompletedWithWarning` case producing `ok:true, status:"warning", warning, warning_detail` shape
- [ ] 3.2 In `UnityPuerExecProtocol.BuildErrorDetailJson`, add branch for `async_result_not_supported` with a human-readable explanation that the function body executed but the return value was a Promise
- [ ] 3.3 In `UnityPuerExecProtocol.TryBuildWrappedScript`, rewrite the thenable detection to call `__bridge.CompleteJobWithWarning(...)` instead of throwing `Error('async_result_not_supported')`; use if-else to separate the warning path from the synchronous result path

## 4. CLI: Exit code and response routing

- [ ] 4.1 In `direct_exec_client.py`, add `"warning"` to the recognized status set in `_status_to_exit_code` so it returns exit code 0 and routes to stdout (same path as `completed` / `running`)

## 5. CLI: Help text and guidance matrix

- [ ] 5.1 In `help_surface.py` Timeout Rules (line ~332), reword "Promise return values are rejected" to clarify that the function body still executes but the return value cannot be serialized
- [ ] 5.2 In `help_surface.py` failure status list (line ~351), update the `failed` entry to remove the Promise clause (now covered by warning); keep the entry for genuine execution errors
- [ ] 5.3 In `help_surface.py` `GUIDANCE_MATRIX`, add `("exec","warning")` entry with `situation` explaining the script body executed but returned a Promise, and `next_steps` directing toward `wait-for-result-marker`
- [ ] 5.4 In `help_surface.py` `GUIDANCE_MATRIX`, update `("exec","failed")` entry — remove the Promise clause from `situation` so it only describes unexpected execution errors

## 6. Tests

- [ ] 6.1 In `tests/test_unity_session_cli.py`, update assertion at line ~276 from "Promise return values are rejected" to new wording
- [ ] 6.2 In `tests/test_real_host_integration.py`, update status assertion at line ~292 from `"failed"` to `"warning"` for the async result test case
- [ ] 6.3 In `tests/test_package_layout.py`, verify line ~136 still finds `async_result_not_supported` in the protocol source (should still pass if the string is preserved in warning code)
- [ ] 6.4 Run the full test suite and verify all tests pass

## 7. Finalize

- [ ] 7.1 Run `openspec status --change "exec-async-warning-status"` to confirm all artifacts are complete
- [ ] 7.2 Verify `git diff --stat` shows only intended files changed
