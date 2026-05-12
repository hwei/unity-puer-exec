## MODIFIED Requirements

### Requirement: Async execution remains machine-usable without continuation tokens

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL return `log_range` and `brief_sequence` in every response so callers can observe the operation window without an opt-in flag. `log_range.start` SHALL be the authoritative observation checkpoint for `wait-for-log-pattern` and `wait-for-result-marker`, replacing the former `log_offset` field. Any response that includes `brief_sequence` SHALL use the compact run encoding defined by `log-brief` rather than a fully expanded repeated-character string. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The extraction modes that return plain text and parsed JSON SHALL be mutually exclusive. The CLI SHALL provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

The `exec` entry function SHALL return an immediate JSON-serializable value for top-level `result`. The runtime SHALL NOT automatically await Promise or thenable return values from the default-exported entry function. Promise- or thenable-returning entry functions MUST complete with a `warning` terminal status (code `async_result_not_supported`) so callers understand the function body executed but the return value could not be captured. Long-running async work continues to use result-marker observation instead of implicit return awaiting.

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

#### Scenario: Caller observes a long import-heavy request

- **WHEN** `exec`, `wait-for-exec`, or another observation-carrying response spans a long run of repeated brief kinds
- **THEN** `brief_sequence` stays compact enough for machine parsing and human scanning
- **AND** the compact form remains a faithful representation of the underlying observed brief order

#### Scenario: Entry function returns a Promise

- **WHEN** the default-exported exec entry function returns a Promise or thenable
- **THEN** `exec` completes with `ok: true`, `status: "warning"`, and `warning: "async_result_not_supported"`
- **AND** the response includes `warning_detail` explaining that the function body executed but the return value could not be serialized
- **AND** the contract does not treat Promise return values as an implicit long-running completion channel

#### Scenario: Agent reads help for exec script authoring

- **WHEN** an agent reads `exec --help` or an exec authoring example
- **THEN** help shows the required default-exported module entry shape
- **AND** help explains that immediate return values populate top-level `result`
- **AND** help explains that Promise return values produce a `warning` status (the function body still executes but the return value cannot be serialized to JSON) instead of being implicitly awaited
