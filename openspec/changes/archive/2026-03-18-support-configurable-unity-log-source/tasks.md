# Tasks

## 1. Contract

- [x] Define `session_marker` as the boundary after which the session artifact becomes the authority for `effective_log_path`
- [x] Define `--unity-log-path` as the explicit pre-session override for non-default log locations

## 2. Implementation

- [x] Extend the session artifact to persist `effective_log_path` once a valid `session_marker` exists
- [x] Add `--unity-log-path` to project-scoped commands that may launch Unity or observe logs before `session_marker` exists
- [x] Update CLI log-source resolution to prefer artifact `effective_log_path`, otherwise fall back to explicit `--unity-log-path`, otherwise the platform default path
- [x] Ensure `get-log-source` reports the same effective source used by observation commands

## 3. Validation

- [x] Add tests for pre-session custom log-path usage and post-session artifact-based recovery
- [x] Add real-host validation evidence for launch-time custom log-path handling
