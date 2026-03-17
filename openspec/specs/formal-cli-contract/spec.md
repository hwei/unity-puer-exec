# Formal CLI Contract

## Purpose

Define the durable machine-facing contract for the `unity-puer-exec` CLI, including command surface, selector rules, log-driven long-running observation, structured output, exit codes, and help discoverability.

## Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `wait-for-result-marker`, `get-log-source`, `exec`, and `ensure-stopped`.

#### Scenario: Agent discovers the CLI surface

- **WHEN** repository docs or help describe the CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are described only as compatibility paths, not as the authoritative surface

### Requirement: Selector-driven commands use mutually exclusive addressing

Selector-driven commands SHALL accept exactly one of `--project-path` or `--base-url`. Supplying both MUST be treated as a usage error. Project-path resolution SHALL follow the repository-wide deterministic resolution order.

#### Scenario: Caller supplies both selectors

- **WHEN** a selector-driven command receives both `--project-path` and `--base-url`
- **THEN** the command reports a usage error
- **AND** machine-readable output surfaces `address_conflict` when structured output is produced

### Requirement: `wait-until-ready` is the explicit readiness shortcut

`wait-until-ready` SHALL act as the explicit readiness-oriented command. In project-path mode it MAY discover or prepare Unity enough for normal use. In base-url mode it SHALL confirm readiness of the directly addressed service without taking ownership of Unity launch.

#### Scenario: Project-scoped readiness is requested

- **WHEN** `wait-until-ready --project-path ...` is invoked
- **THEN** the command may discover an existing session or prepare Unity until the target becomes usable
- **AND** a successful result reports `result.status = "recovered"`

### Requirement: `exec` is the primary work command

`exec` SHALL send JavaScript to the Unity-side execution service. It SHALL accept exactly one selector and exactly one script input source. In project-path mode it MAY implicitly prepare Unity enough to satisfy the request. In base-url mode it SHALL target an already chosen service without owning Unity launch.

#### Scenario: Project-scoped execution is requested

- **WHEN** `exec --project-path ...` is invoked with valid script input
- **THEN** the command may prepare Unity as needed for the execution request
- **AND** the command returns either `status = "completed"` or `status = "running"`

### Requirement: Async execution remains machine-usable without continuation tokens

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL provide enough machine-readable information for a caller to observe the intended long-running work, including an explicit opt-in path for returning the observation start offset used by result-marker waiting. When that opt-in path is requested, `exec` SHALL return top-level `log_offset` consistently for both `completed` and `running` responses. That `log_offset` SHALL be measured against the same log source consumed by `wait-for-log-pattern` and `wait-for-result-marker`, so callers can rely on it as an observation checkpoint. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The extraction modes that return plain text and parsed JSON SHALL be mutually exclusive. The CLI SHALL provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

#### Scenario: Long-running script uses a correlation-aware result marker

- **WHEN** `exec` starts a script that emits a correlation-specific terminal result marker into the Unity log
- **THEN** the initial `exec` response includes enough machine-readable information for the caller to observe that marker
- **AND** when the caller explicitly requests log offset capture, the response includes the observation start offset
- **AND** the caller can use either `wait-for-log-pattern` with extraction or `wait-for-result-marker` to detect and extract the intended terminal marker without polling a dedicated `get-result` command

#### Scenario: Caller starts observation from the returned checkpoint

- **WHEN** a caller invokes `exec --include-log-offset` and then starts either `wait-for-result-marker` or `wait-for-log-pattern` from the returned `log_offset`
- **THEN** the returned offset is compatible with the observer's actual log source
- **AND** the caller does not need to fall back to scanning from the beginning of the log to find the intended marker

#### Scenario: Alias ignores non-matching marker candidates while waiting

- **WHEN** `wait-for-result-marker` observes lines with the standard marker prefix but the extracted JSON is invalid or the `correlation_id` does not match the requested value
- **THEN** those lines are treated as non-matching candidates rather than terminal command failures
- **AND** the command continues waiting until a matching marker is found or the normal wait termination condition is reached

### Requirement: Session identity is not tied only to result continuation

If session identity checking is needed for safe execution or observation, the formal CLI SHALL expose it as a command-level guard rather than as behavior unique to token-driven continuation. Commands that support session guards SHALL fail explicitly when the addressed session does not match the expected session.

#### Scenario: Caller requires same-session observation

- **WHEN** a caller starts work and later waits with an explicit expected session identity
- **THEN** the relevant command reports a machine-readable failure if the addressed session no longer matches
- **AND** the CLI does not silently treat a replacement session as equivalent

#### Scenario: Caller does not require same-session observation

- **WHEN** a caller waits for a result marker without providing an expected session identity
- **THEN** the command may continue observing based on the selected log source and other supplied filters
- **AND** the absence of a session guard does not itself count as a usage error

### Requirement: Observation and stop commands keep their boundary

`wait-for-log-pattern` and `get-log-source` SHALL remain observation commands. `ensure-stopped` SHALL remain the stopped-state command. Observation commands MUST NOT imply Unity launch ownership, and `ensure-stopped` in base-url mode MUST NOT kill the target.

#### Scenario: Agent checks observable log source

- **WHEN** `get-log-source` succeeds
- **THEN** the result reports `result.status = "log_source_available"`
- **AND** the payload includes stable `result.source`

#### Scenario: Agent ensures a base-url target is stopped

- **WHEN** `ensure-stopped --base-url ...` is invoked
- **THEN** the command may inspect state only
- **AND** it does not perform kill behavior against that direct-service target

### Requirement: Formal command results are machine-readable JSON

All formal command results SHALL be machine-readable JSON. Successes and expected non-success machine states that an agent can branch on MUST be emitted on stdout. stderr SHALL be reserved for unstructured usage text or unexpected process-level diagnostics.

#### Scenario: Agent consumes a branchable machine state

- **WHEN** a formal command returns an expected non-success machine state such as `running`, `compiling`, `not_available`, `no_observation_target`, or `not_stopped`
- **THEN** stdout carries the authoritative JSON payload
- **AND** the payload includes stable top-level fields for that command family

### Requirement: Exit codes remain part of the formal machine contract

The CLI SHALL preserve the baseline exit-code model for successful completion, expected machine states, usage errors, and unexpected failures so callers can branch without parsing prose diagnostics.

#### Scenario: Expected machine state completes without success

- **WHEN** a command returns an expected machine state such as `running`, `compiling`, `not_available`, `session_missing`, `session_stale`, `no_observation_target`, or `not_stopped`
- **THEN** the process exits with the corresponding formal non-zero code instead of collapsing all branchable states into one generic failure code

### Requirement: Help is sufficient for agent discovery

Top-level and per-command help SHALL describe the single-entry model, the flat command list, selector exclusivity, workflow examples, key success states, expected non-success states, and minimal invocation examples without requiring repository skill docs as the primary discovery path.

#### Scenario: Agent reads help to discover normal workflow

- **WHEN** an agent reads `unity-puer-exec --help`
- **THEN** help explains the normal `exec` plus result-marker observation workflow
- **AND** help also explains readiness, observation, and stopped-state workflows
