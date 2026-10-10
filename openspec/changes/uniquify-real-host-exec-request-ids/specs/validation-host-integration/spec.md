## ADDED Requirements

### Requirement: Real-host exec request ids are unique per invocation

A real-host test that submits an exec SHALL choose a request id that is different on every invocation of that test in the same process. The id SHALL NOT be derived only from the process id.

#### Scenario: The same case runs twice in one process

- **WHEN** a real-host case builds the request id for an exec
- **AND** the same case builds another request id without restarting the process
- **THEN** the two ids are different
- **AND** the second submission is a new execution rather than a replay of the first
