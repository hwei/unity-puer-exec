## MODIFIED Requirements

### Requirement: Log source resolution supports custom project-scoped paths

CLI log-related commands SHALL support an effective Unity log source that is not limited to the platform default Editor log path. After a valid `session_marker` exists, the CLI SHALL treat the session artifact as the authoritative source for `effective_log_path`. Before a valid `session_marker` exists, callers that depend on a non-default log location SHALL provide `--unity-log-path`. When neither is available, the CLI SHALL prefer the console log path reported by a reachable control service over the platform default path, and SHALL fall back to the platform default path only when no reported path can be obtained. `get-log-source` SHALL report which of these tiers produced the effective path, so a caller can distinguish an observed log the Editor named from one the CLI assumed.

#### Scenario: Post-session observation uses the artifact log path

- **WHEN** a valid session artifact exists with both `session_marker` and `effective_log_path`
- **THEN** `get-log-source` reports that effective path
- **AND** log-observation commands use the same path for waiting and extraction

#### Scenario: Pre-session observation requires an explicit non-default path

- **WHEN** a caller relies on a non-default Unity log path before a valid `session_marker` exists
- **THEN** the caller provides `--unity-log-path` on the log-related command
- **AND** the CLI uses that explicit path instead of the platform default path

#### Scenario: Reported path outranks the platform default

- **WHEN** no explicit `--unity-log-path` and no session artifact `effective_log_path` are available
- **AND** a reachable control service reports a console log path
- **THEN** the CLI uses the reported path
- **AND** the CLI does not use the platform default path

#### Scenario: Caller can tell a named path from an assumed one

- **WHEN** a caller invokes `get-log-source`
- **THEN** the response identifies which resolution tier produced the effective path
- **AND** a path obtained from the control service is distinguishable from the platform default fallback

### Requirement: Launch-driven sessions can request a custom Unity log path

When `unity-puer-exec` launches Unity for a project-scoped workflow, the CLI SHALL support a caller-controlled path for the Unity Editor log so launch-driven sessions can intentionally avoid the default log location. When no caller-controlled path is supplied, the CLI SHALL still avoid the platform default per-user log location and launch the Editor against a log private to the target project, so an unrelated Editor cannot share the log the session is observed through.

#### Scenario: Caller requests a custom log file during launch

- **WHEN** a caller invokes a launch-driven command with `--unity-log-path <path>`
- **THEN** Unity is launched with that log-path override
- **AND** before `session_marker` is available, later log-related commands may continue providing the same `--unity-log-path`
- **AND** once `session_marker` exists, the session artifact records `effective_log_path` so later commands can omit the flag

#### Scenario: Launch without an explicit path still avoids the shared log

- **WHEN** a caller invokes a launch-driven command without `--unity-log-path`
- **THEN** Unity is launched against a log location private to the target project
- **AND** that location is distinct from the platform default per-user Editor log
- **AND** the session artifact records it as `effective_log_path` so later commands need no flag
