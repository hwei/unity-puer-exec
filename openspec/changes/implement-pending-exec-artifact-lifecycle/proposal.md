## Why

The archived spike `harden-pending-exec-artifact-lifecycle` confirmed that project-scoped `exec` now relies on a minimal pending artifact under the Unity host project's `Temp/UnityPuerExec/pending_exec/` directory to preserve the accepted `running -> wait-for-exec` lifecycle. That spike also confirmed the current implementation still lacks an explicit retention policy, stale-file cleanup, malformed-artifact handling, and centralized terminal cleanup, so the lifecycle contract now needs to be made durable before the temporary bridge logic grows further.

## What Changes

- Define the durable pending exec artifact lifecycle for project-scoped `exec` and `wait-for-exec`, including retained metadata, bounded retention, stale cleanup, and terminal deletion rules.
- Keep caller-visible follow-up semantics simple by treating expired or malformed pending artifacts as non-recoverable `missing` outcomes while still cleaning up the local leftovers opportunistically.
- Update the CLI implementation and tests so pending artifact cleanup decisions are centralized instead of scattered across individual recovery branches.
- Add focused host-validation expectations proving the accepted `exec -> running -> wait-for-exec` recovery path still works after lifecycle hardening.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: clarify the durable lifecycle and caller-visible behavior for retained, expired, malformed, and terminally completed pending exec artifacts.
- `validation-host-integration`: require real-host validation that the hardened lifecycle still preserves the normal project-scoped `exec -> wait-for-exec` recovery path.

## Impact

- Affected code: `cli/python/unity_session_logs.py`, `cli/python/unity_puer_exec_runtime.py`, `cli/python/unity_puer_exec.py`, and related tests under `tests/`.
- Affected behavior: project-scoped accepted exec recovery, stale pending artifact cleanup, and `wait-for-exec` handling for expired or malformed local records.
- Affected validation: repository unit coverage plus at least one real-host lifecycle validation pass against `UNITY_PROJECT_PATH`.
