## ADDED Requirements

### Requirement: Real-host validation applies repository-local `.env` launch inputs

Real-host validation SHALL apply repository-local `.env` launch inputs even though it selects the host with an explicit `--project-path`. In particular, `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` loaded from `.env` SHALL reach the Unity launch this repository performs, so a host that needs an extra switch (for example a graphics API switch) can be brought up by the suite without per-command flags. Documented precedence SHALL be preserved: a value set explicitly in the process environment overrides the `.env` value, and the explicit project selection is unchanged.

#### Scenario: Host switch from `.env` reaches the launched Editor

- **WHEN** the validation host needs an extra Unity switch and `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is set only in repository-local `.env`
- **THEN** the Editor the suite launches includes that switch in its argv
- **AND** the suite does not need a per-command flag to supply it

#### Scenario: Process environment overrides `.env`

- **WHEN** `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is present in both the process environment and `.env`
- **THEN** the process-environment value is the one applied to the launch
- **AND** explicitly selecting the host project remains unchanged

#### Scenario: Explicit project selection is unaffected

- **WHEN** a caller supplies `--project-path` for the validation host and `.env` also contains `UNITY_PROJECT_PATH`
- **THEN** the explicit `--project-path` still selects the host
- **AND** loading `.env` does not override the explicit selection
