## ADDED Requirements

### Requirement: Real-host run instructions document host-required Unity launch arguments

The repository's real-host run instructions SHALL state how a contributor supplies Unity launch arguments that a particular validation host needs in order for CLI auto-launch to succeed (for example a graphics API switch), including the ambient environment variable `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` as a JSON array of strings and its relationship to CLI-driven Editor launch.

#### Scenario: Contributor prepares a host that needs an extra Unity switch

- **WHEN** a contributor consults the real-host run instructions for a host that cannot start without an extra Unity argument
- **THEN** the instructions name `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS`
- **AND** the instructions show a JSON-array example such as `["-force-gles30"]`
- **AND** the instructions state that CLI auto-launch of the host picks the value up without per-command flags
