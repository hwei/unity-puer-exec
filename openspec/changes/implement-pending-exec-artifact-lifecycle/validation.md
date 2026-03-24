## Validation Summary

Date: 2026-03-24

### Unit Coverage

Command:

```powershell
python -m unittest tests.test_unity_session_modules tests.test_unity_session_cli
```

Outcome:

- Passed.
- Coverage now includes pending artifact schema metadata, timestamp refresh, expiry cleanup, malformed artifact cleanup, stale-sibling sweep, help text for `missing`, and project-scoped `wait-for-exec` behavior for expired or still-recoverable pending records.

Note:

- The test run still emits the existing argparse usage text from the mutual-exclusion coverage around `wait-for-log-pattern`; the suite nevertheless passed and this change did not alter that behavior.

### Real-Host Lifecycle Check

Prepared host:

```powershell
python tools/prepare_validation_host.py --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project"
```

Observed precondition:

```powershell
python cli/python/unity_puer_exec.py ensure-stopped --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project" --timeout-seconds 10
```

- Returned `status = "not_stopped"` with a live project-scoped session, so the validation continued against the already-running editor instead of forcing a destructive stop.

Lifecycle commands:

```powershell
python cli/python/unity_puer_exec.py exec --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project" --file .tmp/cleanup_add_ints_validation.js --wait-timeout-ms 20000
python cli/python/unity_puer_exec.py exec --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project" --file .tmp/write_add_ints_validation.js --wait-timeout-ms 20000
python cli/python/unity_puer_exec.py exec --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project" --refresh-before-exec --file .tmp/call_add_ints_validation.js --wait-timeout-ms 20000
python cli/python/unity_puer_exec.py wait-for-exec --project-path "F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project" --request-id 0ce48e4f914a4f9ebc417e50f81f3030 --wait-timeout-ms 30000
```

Observed outcomes:

- The refreshed exec returned caller-facing `status = "running"` with `phase = "compiling"` and `request_id = "0ce48e4f914a4f9ebc417e50f81f3030"`.
- `wait-for-exec` completed the same request id successfully with `result.value = 12`.
- A follow-up directory check confirmed `Temp/UnityPuerExec/pending_exec/` was empty after completion, so the terminal cleanup path still removed the pending artifact.

Conclusion:

- The hardened lifecycle preserved the intended real-host `exec -> running -> wait-for-exec -> completed` recovery flow and did not leave the completed request's pending artifact behind.
