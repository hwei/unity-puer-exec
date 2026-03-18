## MODIFIED Requirements

### Requirement: CLI observation uses the effective Unity log source

CLI log-related commands SHALL support an effective Unity log source that is not limited to the platform default Editor log path. After a valid `session_marker` exists, the CLI SHALL treat the session artifact as the authoritative source for `effective_log_path`. Before a valid `session_marker` exists, callers that depend on a non-default log location SHALL provide `--unity-log-path`; otherwise the CLI MAY fall back to the platform default path.

#### Scenario: Post-session observation uses the artifact log path

- **WHEN** a valid session artifact exists with both `session_marker` and `effective_log_path`
- **THEN** `get-log-source` reports that effective path
- **AND** log-observation commands use the same path for waiting and extraction

#### Scenario: Pre-session observation requires an explicit non-default path

- **WHEN** a caller relies on a non-default Unity log path before a valid `session_marker` exists
- **THEN** the caller provides `--unity-log-path` on the log-related command
- **AND** the CLI uses that explicit path instead of the platform default path

### Requirement: Launch-driven sessions can request a custom Unity log path

When `unity-puer-exec` launches Unity for a project-scoped workflow, the CLI SHALL support a caller-controlled path for the Unity Editor log so launch-driven sessions can intentionally avoid the default log location.

#### Scenario: Caller requests a custom log file during launch

- **WHEN** a caller invokes a launch-driven command with `--unity-log-path <path>`
- **THEN** Unity is launched with that log-path override
- **AND** before `session_marker` is available, later log-related commands may continue providing the same `--unity-log-path`
- **AND** once `session_marker` exists, the session artifact records `effective_log_path` so later commands can omit the flag
