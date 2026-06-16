## MODIFIED Requirements

### Requirement: Observation and stop commands keep their boundary

`wait-for-log-pattern` and `get-log-source` SHALL remain observation commands. `ensure-stopped` SHALL remain the stopped-state command. Observation commands MUST NOT imply Unity launch ownership, and `ensure-stopped` in base-url mode MUST NOT kill the target. Process-liveness detection used by `ensure-stopped` SHALL be independent of the host operating system's display language, so that a recorded session PID that is no longer running is reported as stopped regardless of locale.

#### Scenario: Agent checks observable log source

- **WHEN** `get-log-source` succeeds
- **THEN** the result reports `result.status = "log_source_available"`
- **AND** the payload includes stable `result.source`

#### Scenario: Agent ensures a base-url target is stopped

- **WHEN** `ensure-stopped --base-url ...` is invoked
- **THEN** the command may inspect state only
- **AND** it does not perform kill behavior against that direct-service target

#### Scenario: Stopped detection does not depend on OS display language

- **WHEN** `ensure-stopped` (project-path mode) evaluates a recorded session PID that is no longer running on a non-English Windows host
- **THEN** the command reports the target as `stopped`
- **AND** it does not classify the dead PID as still running because of a localized process-listing message
