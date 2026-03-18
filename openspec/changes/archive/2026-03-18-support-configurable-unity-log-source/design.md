# Design

## Goals

- allow CLI observation commands to use the actual Unity log source even when it is not the platform default path
- allow launch-driven workflows to opt into a custom Unity log path
- keep the default path as a fallback, not the only supported source

## Non-Goals

- changing the current result-marker workflow
- solving the current `log_offset` bug in this change; that work remains tracked separately

## Preferred Direction

The CLI should treat the session artifact as the authoritative source for the effective Unity log path, but only after a valid `session_marker` has been established. Before a caller has obtained a `session_marker`, the CLI should not assume a non-default log path unless the caller explicitly provides one.

## Candidate Contract Shape

### Observation

Log-related commands should resolve their effective log source using the following model:

- after a valid `session_marker` exists, prefer `effective_log_path` recorded in the session artifact
- before a valid `session_marker` exists, a caller that depends on a non-default path must explicitly provide `--unity-log-path`
- when neither a valid artifact path nor an explicit override is available, fall back to the platform default path

This makes `session_marker` the boundary between a pre-session launch/setup phase and a stable session-observation phase.

### Launch

When `unity-puer-exec` launches Unity itself, the launch path should support an explicit `--unity-log-path` override. That override is required for stable pre-session observation when the caller intentionally avoids the default log location.

The intended workflow is:

- caller launches or waits with `--unity-log-path <path>`
- before `session_marker` is available, log-related commands that rely on that non-default path continue passing the same `--unity-log-path`
- once `session_marker` is available, the session artifact records `effective_log_path` and later commands can omit the flag

### Command Scope

The `--unity-log-path` parameter should be available on project-scoped commands that may launch Unity or depend on log observation before `session_marker` is available. At minimum this includes:

- `wait-until-ready`
- `get-log-source`
- `wait-for-log-pattern`
- `wait-for-result-marker`

## Validation

Host validation should prove at least:

- default-path observation still works
- a non-default log path can be observed before `session_marker` exists when the caller explicitly provides `--unity-log-path`
- after `session_marker` exists, the session artifact supplies the effective log path and later commands no longer need the flag
- launch-driven sessions can align `wait-for-log-pattern` and `wait-for-result-marker` with the same effective log source
