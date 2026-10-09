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

#### Scenario: A base-url request stays continuable while its refresh has not settled

- **WHEN** a base-url `exec` returns a non-terminal refreshing or compiling phase for a request the addressed service has not accepted
- **THEN** continuing that request with `wait-for-exec --base-url --request-id <id>` converges on the script result instead of answering `missing`
- **AND** the CLI either keeps resubmitting the request until the script runs or reports a terminal outcome naming the exhausted budget
- **AND** the CLI does not present `wait-for-exec --request-id` as the continuation for a request whose record exists nowhere

#### Scenario: Caller observes an intermediate refreshing or compiling phase

- **WHEN** an exec request is still refreshing or compiling when a response is returned
- **THEN** the response represents a non-terminal accepted state rather than a terminal result
- **AND** the response makes the continuation path explicit so the caller can wait for the eventual script result

## ADDED Requirements

### Requirement: Help states that an automatic refresh settles on its own budget

The formal CLI help surface SHALL state that the compile cycle an automatic refresh starts is settled on a compile-scale budget of its own, and that this settle is not bounded by `--wait-timeout-ms`. The statement SHALL appear wherever `exec` describes its wait or timeout behavior, not only in the automatic-refresh description, so a caller choosing a small request-wait budget does not infer that a refresh is abandoned at that value. The status surface SHALL not imply the opposite.

#### Scenario: Agent reads exec help and learns the settle is not the request-wait budget

- **WHEN** a caller reads `exec --help`
- **THEN** the help states that an automatic refresh settles its compile cycle on a compile-scale budget
- **AND** it states that `--wait-timeout-ms` does not bound that settle
- **AND** the statement appears in the wait or timeout guidance, not only in the automatic-refresh description

#### Scenario: Agent reads exec status help and is not misled

- **WHEN** a caller reads `exec --help-status`
- **THEN** nothing on that surface implies that `--wait-timeout-ms` bounds an automatic refresh's settle
- **AND** the surface stays consistent with the statement made by `exec --help`

#### Scenario: Agent reads wait-for-compile help and finds the same cycle described consistently

- **WHEN** a caller reads `wait-for-compile --help`
- **THEN** the `--settle-timeout-seconds` description and the `exec` statement describe the same compile cycle
- **AND** neither surface contradicts the other
