## MODIFIED Requirements

### Requirement: CLI observation uses the effective Unity log source

CLI observation commands SHALL support an effective Unity log source that is not limited to the platform default Editor log path. When Unity can provide an explicit log path for the selected target, the CLI SHALL prefer that effective source over a guessed default path. When no explicit source is available, the CLI MAY fall back to the current default platform path.

#### Scenario: Unity exposes a non-default log path

- **WHEN** the selected Unity target exposes an effective log path that differs from the platform default
- **THEN** `get-log-source` reports that effective path
- **AND** log-observation commands use the same path for waiting and extraction

### Requirement: Launch-driven sessions can request a custom Unity log path

When `unity-puer-exec` launches Unity for a project-scoped workflow, the CLI SHALL support a caller-controlled path for the Unity Editor log so launch-driven sessions can intentionally avoid the default log location.

#### Scenario: Caller requests a custom log file during launch

- **WHEN** a caller invokes a launch-driven command with a custom Unity log path
- **THEN** Unity is launched with that log-path override
- **AND** subsequent observation commands can resolve and use the same effective path
