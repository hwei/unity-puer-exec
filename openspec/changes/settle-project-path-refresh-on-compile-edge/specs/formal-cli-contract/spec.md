# Spec Delta

## MODIFIED Requirements

### Requirement: Automatic refresh is a non-terminal phase of the accepted exec request

When the server reports that it triggered an automatic refresh, the CLI SHALL treat the refresh and the resulting compilation as non-terminal phases of the same accepted exec request. The CLI SHALL NOT present a refresh confirmation as the caller's script result, and SHALL make the continuation path explicit so that a caller does not mistake an intermediate phase for completion. The settle that precedes the one permitted resubmit SHALL be edge-aware in every selector mode, waiting within a bounded appear window for a compilation to appear rather than only for an already-visible compilation to finish, so a refresh the service resolves without compiling converges inside the same invocation whichever selector the caller used.

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

#### Scenario: An exhausted base-url refresh budget is its own terminal outcome

- **WHEN** a base-url `exec` cannot settle the compile cycle an automatic refresh started before its compile-scale budget expires, or the refresh still triggers on the one resubmit it is permitted
- **THEN** the response reports the non-success status `refresh_unsettled` with its own exit code, distinct from `missing`
- **AND** the payload states that the script has not run and that no replayable record exists for the request
- **AND** the payload carries a `next_steps` resubmit path using the same `request_id`
- **AND** the CLI reports this only for a request the service never accepted, so resubmitting cannot run a script that already ran

#### Scenario: Continuation guidance names only continuations that work

- **WHEN** a response offers `wait-for-exec --request-id` as a continuation
- **THEN** the addressed service holds a replayable record for that `request_id` at the moment the guidance is built
- **AND** a request the CLI itself left unsettled offers no `wait-for-exec` continuation

#### Scenario: Caller observes an intermediate refreshing or compiling phase

- **WHEN** an exec request is still refreshing or compiling when a response is returned
- **THEN** the response represents a non-terminal accepted state rather than a terminal result
- **AND** the response makes the continuation path explicit so the caller can wait for the eventual script result

#### Scenario: A project-path settle waits for the compile edge, not only for readiness

- **WHEN** the server triggers an automatic refresh for a project-path `exec`
- **AND** the Editor is already reachable and reports `ready` because no compilation has started yet
- **THEN** the CLI waits within its bounded appear window for a compilation to appear before it re-submits
- **AND** it does not re-submit on the first `ready` observation alone

#### Scenario: Both selectors spend the same budgets on the same cycle

- **WHEN** an automatic refresh is settled in project-path mode and in base-url mode
- **THEN** both spends use the same bounded appear window and the same compile-scale settle budget
- **AND** neither is bounded by `--wait-timeout-ms`

#### Scenario: A refresh the service resolves without compiling converges in one project-path invocation

- **WHEN** a project-path `exec` triggers an automatic refresh for content the service then
  suppresses as already handed to a dispatched refresh
- **AND** Unity starts no compilation
- **THEN** the single permitted resubmit reaches a terminal response carrying the script result
- **AND** the invocation does not report the non-terminal refreshing phase

#### Scenario: An unfinished cycle is still non-terminal, not settled

- **WHEN** the project-path settle's compile cycle does not finish before the compile-scale budget
  expires
- **THEN** the CLI reports the same non-terminal outcome it reports today
- **AND** it does not treat the exhausted budget as a settled compile
