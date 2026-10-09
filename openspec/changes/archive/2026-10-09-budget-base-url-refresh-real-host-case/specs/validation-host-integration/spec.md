# Spec Delta

## ADDED Requirements

### Requirement: Real-host automatic-refresh cases budget the refresh at the compile scale

The repository-owned real-host validation workflow SHALL budget a request that triggers an
automatic refresh with a compile-scale wait, so the CLI's settle-and-resubmit loop reaches
the terminal response the refresh path produces. Such a case SHALL assert the refresh
disclosure on that terminal response and SHALL NOT depend on a continuation fetched by a
different command to carry the refresh decision.

#### Scenario: Refresh-triggering base-url case reaches the terminal exec response

- **WHEN** a real-host case makes a code change that triggers an automatic refresh, then
  runs `exec` against the host's control endpoint
- **THEN** the request is given a compile-scale wait budget
- **AND** the case asserts `refresh.triggered` and the `compile_triggering_change` reason on
  the terminal `exec` response
- **AND** the payload it asserts on is not a `wait-for-exec` continuation

#### Scenario: A request budget shorter than the refresh settle fails the case

- **WHEN** a refresh-triggering request returns a non-terminal response because its wait
  budget ended before the settle completed
- **THEN** the case does not treat a later continuation's payload as evidence that the
  refresh decision was disclosed
- **AND** the case fails with that expectation named
