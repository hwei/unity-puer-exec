## MODIFIED Requirements

### Requirement: Automatic refresh is a non-terminal phase of the accepted exec request

When the server reports that it triggered an automatic refresh, the CLI SHALL treat the refresh and the resulting compilation as non-terminal phases of the same accepted exec request. The CLI SHALL NOT present a refresh confirmation as the caller's script result, and SHALL make the continuation path explicit so a caller does not mistake an intermediate phase for completion.

#### Scenario: Automatic refresh runs the script after settling

- **WHEN** the server triggers an automatic refresh and the refresh triggers a compilation
- **THEN** the CLI settles on the compile cycle before running the caller's script
- **AND** the terminal response carries the script result, not a refresh confirmation

#### Scenario: Automatic refresh survives its own domain reload

- **WHEN** the server triggers an automatic refresh whose compilation completes with a domain reload
- **AND** the caller is still continuing the same accepted request (for example via `wait-for-exec --request-id`)
- **THEN** the CLI does not surface a non-recoverable terminal outcome such as `missing` for that request
- **AND** it either recovers the same request once the reload completes or resubmits the script as a new attempt
- **AND** the eventual terminal response carries the script result, not a refresh confirmation or an "unrecoverable request" error

#### Scenario: Caller observes an intermediate refreshing or compiling phase

- **WHEN** an exec request is still refreshing or compiling when a response is returned
- **THEN** the response represents a non-terminal accepted state rather than a terminal result
- **AND** the response makes the continuation path explicit so the caller can wait for the eventual script result
