## ADDED Requirements

### Requirement: Real-host runtime validation covers critical CLI workflows
The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path, not only manifest rewiring or mocked Python contracts.

#### Scenario: Contributor runs the critical real-host regression path
- **WHEN** a contributor runs the repository-owned real-host validation workflow against a prepared `UNITY_PROJECT_PATH`
- **THEN** the workflow exercises project-scoped readiness, `exec --include-log-offset`, and both high-level and low-level log-observation commands against the real Unity host
- **AND** the workflow reports failures in a form that distinguishes runtime host-validation regressions from ordinary mocked test failures

### Requirement: Real-host observation validation proves checkpoint compatibility
The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec --include-log-offset` remains compatible with the actual log source consumed by the CLI observation commands.

#### Scenario: Contributor validates observation from the returned checkpoint
- **WHEN** the real-host validation workflow starts an execution that emits a correlation-aware result marker and then observes from the returned `log_offset`
- **THEN** `wait-for-result-marker` succeeds from that checkpoint against the real host
- **AND** `wait-for-log-pattern` with structured extraction can observe the same marker from a compatible checkpoint without falling back to a full-log scan
