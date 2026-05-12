# Exec Warning Status

## Purpose

Define the warning terminal status contract for async exec results, including the response shape, exit code mapping, and distinguishable behavior from genuine failures, so that callers can understand when a script body executed successfully but the return value could not be captured.

## Requirements

### Requirement: Exec warning status for async result returns

When the default-exported `exec` entry function returns a Promise or thenable, the runtime SHALL complete the job with a `warning` terminal status rather than a `failed` status. The `warning` status SHALL communicate that the function body executed successfully but the return value could not be captured because only immediate JSON-serializable results are supported.

The warning response SHALL use the shape: `ok: true`, `status: "warning"`, with fields `warning` (machine-readable code, e.g., `"async_result_not_supported"`) and `warning_detail` (human-readable explanation). The CLI SHALL map `status: "warning"` to exit code 0 and emit the response on stdout. `wait-for-exec` SHALL return the same warning response when the addressed request has reached a warning terminal state.

#### Scenario: Entry function returns a Promise

- **WHEN** the default-exported exec entry function returns a Promise or thenable
- **THEN** `exec` completes with `ok: true`, `status: "warning"`, and `warning: "async_result_not_supported"`
- **AND** the CLI returns exit code 0 with the warning response on stdout
- **AND** the response includes `warning_detail` explaining that the function body executed but the return value could not be serialized
- **AND** the contract does not treat Promise return values as an implicit long-running completion channel

#### Scenario: wait-for-exec observes a warning terminal state

- **WHEN** `wait-for-exec` addresses a request that previously reached a warning terminal state
- **THEN** the command returns immediately with the same warning response shape
- **AND** no further waiting is performed

#### Scenario: Warning response is distinguishable from genuine failures

- **WHEN** an exec script throws a runtime exception (e.g., `TypeError`, `ReferenceError`)
- **THEN** `exec` completes with `ok: false`, `status: "failed"`, and `error` / `stack` fields
- **AND** the CLI returns exit code 1 with the failure response on stderr
- **AND** this is clearly distinct from a warning response which uses `ok: true`, `status: "warning"`, exit code 0, and stdout

### Requirement: Warning detail is self-explanatory in the response

The runtime SHALL include a machine-readable `warning` code and a human-readable `warning_detail` string in every warning response so that callers can understand the situation without consulting external help. The `warning_detail` SHALL state that the entry function body executed, that the return value was a Promise, and that async results should use `console.log` with `wait-for-result-marker` instead.

#### Scenario: Agent receives warning without consulting help

- **WHEN** an agent receives a warning response with `warning: "async_result_not_supported"`
- **THEN** the `warning_detail` field contains enough information for the agent to understand that the script body executed and that async result capture requires a different workflow
- **AND** the agent does not need to run `--help-status` to understand the situation
