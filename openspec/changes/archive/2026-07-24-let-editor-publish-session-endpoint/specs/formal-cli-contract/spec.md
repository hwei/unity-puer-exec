## MODIFIED Requirements

### Requirement: Observation and stop commands keep their boundary

`wait-for-log-pattern` and `get-log-source` SHALL remain observation commands. `ensure-stopped` SHALL remain the stopped-state command. Observation commands MUST NOT imply Unity launch ownership, and `ensure-stopped` in base-url mode MUST NOT kill the target.

In project mode, `ensure-stopped` SHALL decide whether the project is stopped from project-local state — the project's Unity lockfile and the Editor's published endpoint — rather than from a process id recorded earlier or from a machine-wide count of Unity processes. A stop action SHALL target only a process the published endpoint identifies as belonging to the target project. Process-liveness detection SHALL be independent of the host operating system's display language.

#### Scenario: Agent checks observable log source

- **WHEN** `get-log-source` succeeds
- **THEN** the result reports `result.status = "log_source_available"`
- **AND** the payload includes stable `result.source`

#### Scenario: Agent ensures a base-url target is stopped

- **WHEN** `ensure-stopped --base-url ...` is invoked
- **THEN** the command may inspect state only
- **AND** it does not perform kill behavior against that direct-service target

#### Scenario: Project with no running Editor is reported stopped

- **WHEN** `ensure-stopped` (project mode) runs and the project's Unity lockfile is not held
- **THEN** the command reports the target as `stopped`
- **AND** it reports so regardless of how many unrelated Unity Editor processes are running on the machine

#### Scenario: A live Editor is not reported stopped

- **WHEN** `ensure-stopped` (project mode) runs and the project's Unity lockfile is held
- **THEN** the command does not report the target as `stopped`
- **AND** it reports so regardless of whether any earlier session record named a process that has since exited

#### Scenario: A stop action never targets another project

- **WHEN** `ensure-stopped` performs a kill in project mode
- **THEN** the process it targets is the one the target project's published endpoint identifies
- **AND** no process belonging to a different project is targeted

#### Scenario: Stopped detection does not depend on OS display language

- **WHEN** `ensure-stopped` (project-path mode) evaluates process liveness on a non-English Windows host
- **THEN** the reported result reflects actual process state
- **AND** it is not altered by a localized process-listing message

### Requirement: Log source resolution supports custom project-scoped paths

CLI log-related commands SHALL support an effective Unity log source that is not limited to the platform default Editor log path. The CLI SHALL resolve the effective log source in this order: an explicit `--unity-log-path` supplied by the caller, then the console log path published by the project's Editor, then the platform default path as a last resort. The CLI SHALL NOT resolve the effective log path from a session record it wrote itself. `get-log-source` SHALL report which of these tiers produced the effective path, so a caller can distinguish an observed log the Editor named from one the CLI assumed.

#### Scenario: Published path outranks the platform default

- **WHEN** no explicit `--unity-log-path` is supplied
- **AND** the project's Editor publishes a console log path
- **THEN** the CLI uses the published path
- **AND** the CLI does not use the platform default path

#### Scenario: Explicit caller intent wins

- **WHEN** a caller supplies `--unity-log-path` and the Editor publishes a different path
- **THEN** the CLI uses the caller-supplied path

#### Scenario: No published path is available

- **WHEN** no explicit path is supplied and no Editor publication can be read
- **THEN** the CLI falls back to the platform default path as a last resort

#### Scenario: Caller can tell a named path from an assumed one

- **WHEN** a caller invokes `get-log-source`
- **THEN** the response identifies which resolution tier produced the effective path
- **AND** a path obtained from the Editor's publication is distinguishable from the platform default fallback

## ADDED Requirements

### Requirement: A project without a control service is reported, not silently attached

When a project-scoped command finds a running Editor that has not activated a control service, the CLI SHALL report that condition as a distinct non-success status rather than attaching to whatever endpoint answers a candidate port. The report SHALL be actionable: it SHALL state the ways the caller can proceed. When the error path can identify a reachable service owning the project whose bridge version differs from the CLI or is absent, the condition SHALL be reported as `version_mismatch` per `cli-version-compatibility` rather than as a missing opt-in, so the caller is pointed at aligning the installation instead of at an activation mechanism the running bridge does not provide.

#### Scenario: Running Editor has no control service

- **WHEN** a project-scoped command runs, the project's Unity lockfile is held, and no endpoint is published
- **THEN** the command reports a distinct status identifying the Editor as not under CLI control
- **AND** the response states how to proceed rather than only that the command failed

#### Scenario: A version-mismatched bridge is not reported as a missing opt-in

- **WHEN** the project lockfile is held, no endpoint is published, and the error-path scan finds a reachable service owning the project whose bridge version differs from the CLI or is absent
- **THEN** the command reports `version_mismatch`
- **AND** the guidance points at aligning the installation rather than at an activation action the running bridge does not provide

#### Scenario: The refusal is not a launch failure

- **WHEN** this status is reported
- **THEN** it is distinguishable from a failure to launch or a failure to become ready
- **AND** a caller can tell that the remedy is an activation decision rather than a retry
