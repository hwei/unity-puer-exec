## ADDED Requirements

### Requirement: Real-host sequential validation establishes a clean readiness boundary

The repository-owned real-host validation workflow SHALL establish a repeatable boundary between one project-scoped test case ending and the next readiness attempt beginning. A previous case leaving behind a stale session artifact, a fresh `UnityLockfile`, or an incomplete stop result MUST NOT by itself convert the next case into an unexplained readiness stall.

#### Scenario: Contributor runs sequential real-host cases in one suite invocation

- **WHEN** one real-host validation case tears down Unity for the target `UNITY_PROJECT_PATH` and the next case immediately starts another project-scoped readiness attempt
- **THEN** the repository-owned workflow either confirms the previous stop completed, waits until the target is genuinely recoverable, or launches a new editor cleanly
- **AND** a failure reports enough machine-usable state to distinguish incomplete stop or stale recovery evidence from a true runtime readiness regression

## MODIFIED Requirements

### Requirement: Real-host runtime validation covers critical CLI workflows

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path, not only manifest rewiring or mocked Python contracts. For the hardened pending-artifact lifecycle, that workflow SHALL still prove the accepted `exec -> running -> wait-for-exec` recovery path against a real Unity host.

#### Scenario: Contributor runs the critical real-host regression path

- **WHEN** a contributor runs the repository-owned real-host validation workflow against a prepared `UNITY_PROJECT_PATH`
- **THEN** the workflow exercises project-scoped readiness, project-scoped `exec`, and both high-level and low-level log-observation commands against the real Unity host
- **AND** the workflow uses the current exec observation checkpoint surface instead of relying on removed CLI flags
- **AND** the workflow reports failures in a form that distinguishes runtime host-validation regressions from ordinary mocked test failures

#### Scenario: Contributor validates accepted exec recovery after lifecycle hardening

- **WHEN** the real-host validation workflow triggers a project-scoped `exec` path that first returns an accepted non-terminal state and later continues through `wait-for-exec`
- **THEN** the workflow confirms the same `request_id` remains usable through completion
- **AND** the hardened pending-artifact lifecycle does not break the normal `exec -> running -> wait-for-exec` recovery path

### Requirement: Real-host observation validation proves checkpoint compatibility

The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec` remains compatible with the actual log source consumed by the CLI observation commands.

#### Scenario: Contributor validates observation from the returned checkpoint

- **WHEN** the real-host validation workflow starts an execution that emits a correlation-aware result marker and then observes from the checkpoint returned in the exec response
- **THEN** `wait-for-result-marker` succeeds from that checkpoint against the real host
- **AND** `wait-for-log-pattern` with structured extraction can observe the same marker from a compatible checkpoint without falling back to a full-log scan
