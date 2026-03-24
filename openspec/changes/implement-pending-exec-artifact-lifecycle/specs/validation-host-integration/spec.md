## MODIFIED Requirements

### Requirement: Real-host runtime validation covers critical CLI workflows

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path, not only manifest rewiring or mocked Python contracts. For the hardened pending-artifact lifecycle, that workflow SHALL still prove the accepted `exec -> running -> wait-for-exec` recovery path against a real Unity host.

#### Scenario: Contributor runs the critical real-host regression path

- **WHEN** a contributor runs the repository-owned real-host validation workflow against a prepared `UNITY_PROJECT_PATH`
- **THEN** the workflow exercises project-scoped readiness, `exec --include-log-offset`, and both high-level and low-level log-observation commands against the real Unity host
- **AND** the workflow reports failures in a form that distinguishes runtime host-validation regressions from ordinary mocked test failures

#### Scenario: Contributor validates accepted exec recovery after lifecycle hardening

- **WHEN** the real-host validation workflow triggers a project-scoped `exec` path that first returns an accepted non-terminal state and later continues through `wait-for-exec`
- **THEN** the workflow confirms the same `request_id` remains usable through completion
- **AND** the hardened pending-artifact lifecycle does not break the normal `exec -> running -> wait-for-exec` recovery path
