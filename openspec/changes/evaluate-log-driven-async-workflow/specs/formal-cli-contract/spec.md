## MODIFIED Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. If log-driven observation is accepted as the durable long-running workflow, the authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `get-log-source`, `exec`, and `ensure-stopped`, and SHALL no longer require `get-result` as a formal command.

#### Scenario: Agent discovers the CLI surface after async simplification

- **WHEN** repository docs or help describe the CLI after the new workflow is accepted
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** long-running work is described without requiring a separate `get-result` continuation command

### Requirement: Async execution remains machine-usable

If the formal CLI removes token-driven continuation, long-running execution SHALL still remain machine-usable. `exec` SHALL provide enough machine-readable information for a caller to observe the intended long-running work. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The CLI SHALL also provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

#### Scenario: Long-running script uses a correlation-aware result marker

- **WHEN** `exec` starts a script that emits a correlation-specific terminal result marker into the Unity log
- **THEN** the initial `exec` response includes enough machine-readable information for the caller to observe that marker
- **AND** the caller can use either `wait-for-log-pattern` with extraction or `wait-for-result-marker` to detect and extract the intended terminal marker without polling a dedicated `get-result` command

#### Scenario: Alias ignores non-matching marker candidates while waiting

- **WHEN** `wait-for-result-marker` observes lines with the standard marker prefix but the extracted JSON is invalid or the `correlation_id` does not match the requested value
- **THEN** those lines are treated as non-matching candidates rather than terminal command failures
- **AND** the command continues waiting until a matching marker is found or the normal wait termination condition is reached

### Requirement: Session identity is not tied only to result continuation

If session identity checking is needed for safe execution or observation, the formal CLI SHALL expose it as a command-level guard rather than as behavior unique to `get-result`. Commands that support session guards SHALL fail explicitly when the addressed session does not match the expected session.

#### Scenario: Caller requires same-session observation

- **WHEN** a caller starts work and later waits with an explicit expected session identity
- **THEN** the relevant command reports a machine-readable failure if the addressed session no longer matches
- **AND** the CLI does not silently treat a replacement session as equivalent

### Requirement: Help remains sufficient for long-running workflow discovery

Top-level and per-command help SHALL explain the recommended long-running workflow in terms of the accepted durable contract. If log-driven observation replaces token-driven continuation, help SHALL distinguish the low-level regex observation primitive from the recommended result-marker workflow, and SHALL show how `exec` and `wait-for-result-marker` work together, including correlation markers and expected machine states.

#### Scenario: Agent reads help to discover the long-running workflow

- **WHEN** an agent reads `unity-puer-exec --help` and the relevant command help after the new workflow is accepted
- **THEN** help describes the recommended `exec` plus observation workflow without relying on hidden repository skill docs
- **AND** help makes both the low-level regex primitive and the recommended result-marker workflow discoverable from the CLI alone
