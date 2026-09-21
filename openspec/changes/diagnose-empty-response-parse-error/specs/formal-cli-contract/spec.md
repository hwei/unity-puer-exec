## MODIFIED Requirements

### Requirement: Formal command results are machine-readable JSON

All formal command results SHALL be machine-readable JSON. Successes and expected non-success machine states that an agent can branch on MUST be emitted on stdout. stderr SHALL be reserved for unstructured usage text or unexpected process-level diagnostics.

#### Scenario: Agent consumes a branchable machine state

- **WHEN** a formal command returns an expected non-success machine state such as `running`, `compiling`, `not_available`, `no_observation_target`, or `not_stopped`
- **THEN** stdout carries the authoritative JSON payload
- **AND** the payload includes stable top-level fields for that command family

#### Scenario: Command response body is empty or not JSON

- **WHEN** a formal command's response body is empty or cannot be parsed as JSON (for example a bridge response that arrived with no payload)
- **THEN** the CLI emits a structured non-success JSON payload on stdout that names the condition, the operation, and the exit-code meaning
- **AND** it does not surface a raw decode-exception message such as `Expecting value: line 1 column 1 (char 0)` as the caller-facing `error`
- **AND** the payload carries a `next_steps` continuation so an agent can retry or branch without parsing prose
