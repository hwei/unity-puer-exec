## Why

Real-host runs select the host with an explicit `--project-path`, and `unity_session_env.resolve_project_path` returns immediately when a project path is supplied — so repository-local `.env` is never loaded into the process environment for those runs. The repository documents that `.env` is auto-loaded and that a host needing an extra Unity switch sets `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS`, but the real-host path silently ignores it. This was observed in the validation host's `Editor.log` argv, which contained the CLI-owned switches and the new `-disable-assembly-updater` but no `-force-gles30`, even though `.env` sets it. A host that genuinely needs the switch to start would be launched without it, producing misleading launch failures.

## What Changes

- Ensure repository-local `.env` launch inputs reach the Unity launch performed by real-host validation, even when the caller supplies `--project-path`.
- Preserve documented precedence: an explicitly set process-environment value overrides the `.env` value, and explicit `--project-path` still selects the project.
- Keep the fix scoped to the harness/entry path used by real-host validation (or a narrowly scoped early load with no product-behavior change); do not change `launch_unity` merge semantics or CLI-owned switch handling.
- Add coverage proving the `.env` `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` value reaches the launched argv and that a process-env value still wins.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `validation-host-integration`: real-host validation SHALL apply repository-local `.env` launch inputs even though it selects the host with an explicit `--project-path`.

## Impact

- Real-host test entry/prep (`tests/test_real_host_integration.py`) and any shared dotenv helper under `tests/`.
- Possible narrow `unity_session_env` loading change if the fix is product-side; documented precedence (explicit process env, explicit flag) must remain.
- No product CLI behavior change beyond ensuring documented `.env` auto-loading actually applies when `--project-path` is supplied.
