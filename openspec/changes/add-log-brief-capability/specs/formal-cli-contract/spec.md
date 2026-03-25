## MODIFIED Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `wait-for-exec`, `wait-for-result-marker`, `get-log-source`, `get-log-briefs`, `exec`, `ensure-stopped`, and `resolve-blocker`.

#### Scenario: Agent discovers the CLI surface

- **WHEN** repository docs or help describe the CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are described only as compatibility paths, not as the authoritative surface
- **AND** transitional aliases remain thin adapters over the formal command behavior rather than separate feature-bearing command trees

## REMOVED Requirements

### Requirement: Async execution remains machine-usable without continuation tokens

**Reason**: The `--include-log-offset` opt-in and `log_offset` field are superseded by the automatic `log_range` field introduced in the `log-brief` capability. The remainder of this requirement's content is preserved; only the opt-in log offset mechanism is replaced.

**Migration**: Callers that used `exec --include-log-offset` and read `log_offset` from the response SHALL instead read `log_range.start` from the standard response, which is now always present without a flag.

## ADDED Requirements

### Requirement: Async execution remains machine-usable without continuation tokens (revised)

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL return `log_range` and `brief_sequence` in every response so callers can observe the operation window without an opt-in flag. `log_range.start` SHALL be the authoritative observation checkpoint for `wait-for-log-pattern` and `wait-for-result-marker`, replacing the former `log_offset` field. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The extraction modes that return plain text and parsed JSON SHALL be mutually exclusive. The CLI SHALL provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

The `exec` entry function SHALL return an immediate JSON-serializable value for top-level `result`. The runtime SHALL NOT automatically await Promise or thenable return values from the default-exported entry function. Promise- or thenable-returning entry functions MUST fail explicitly so long-running async work continues to use result-marker observation instead of implicit return awaiting.

#### Scenario: Long-running script uses a correlation-aware result marker

- **WHEN** `exec` starts a script that emits a correlation-specific terminal result marker into the Unity log
- **THEN** the initial `exec` response includes `log_range` with a stable `start` offset for the caller to use as the observation checkpoint
- **AND** the caller can use either `wait-for-log-pattern` with extraction or `wait-for-result-marker` starting from `log_range.start` to detect and extract the intended terminal marker without polling a dedicated `get-result` command

#### Scenario: Caller starts observation from the returned checkpoint

- **WHEN** a caller invokes `exec` and then starts either `wait-for-result-marker` or `wait-for-log-pattern` from `log_range.start`
- **THEN** the returned offset is compatible with the observer's actual log source
- **AND** the caller does not need to fall back to scanning from the beginning of the log to find the intended marker

#### Scenario: Alias ignores non-matching marker candidates while waiting

- **WHEN** `wait-for-result-marker` observes lines with the standard marker prefix but the extracted JSON is invalid or the `correlation_id` does not match the requested value
- **THEN** those lines are treated as non-matching candidates rather than terminal command failures
- **AND** the command continues waiting until a matching marker is found or the normal wait termination condition is reached

#### Scenario: Entry function returns a Promise

- **WHEN** the default-exported exec entry function returns a Promise or thenable
- **THEN** `exec` fails explicitly with a machine-readable error
- **AND** the contract does not treat Promise return values as an implicit long-running completion channel
