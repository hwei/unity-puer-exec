## MODIFIED Requirements

### Requirement: Real-host runtime validation covers critical CLI workflows

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path against both the repository-local package wiring path and the published OpenUPM install path when that path is under evaluation. For the published path, the durable record SHALL distinguish package acquisition blockers, import stabilization, and runtime workflow outcome instead of collapsing them into a single undifferentiated failure.

#### Scenario: Contributor validates the published OpenUPM install path against a real host

- **WHEN** a contributor evaluates the published `com.txcombo.unity-puer-exec` package through OpenUPM on the validation host
- **THEN** the repository-owned record states whether package acquisition succeeded, including whether registry access required proxy configuration
- **AND** the workflow waits until Unity import / domain reload activity is sufficiently stable before judging the representative `exec` path as failed
- **AND** the final record separates acquisition friction, editor stabilization friction, and post-install CLI outcome

### Requirement: Real-host observation validation proves checkpoint compatibility

The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec` remains compatible with the actual log source consumed by the CLI observation commands, including the case where a first observation attempt happens during import churn and the same request later becomes recoverable.

#### Scenario: Contributor observes a package-local exec request through import churn

- **WHEN** a contributor starts a package-local `exec` request while the editor is still stabilizing after package installation and the initial transport response is ambiguous or delayed
- **THEN** the durable validation record treats the request as recoverable until `wait-for-exec`, `wait-for-result-marker`, or equivalent follow-up proves otherwise
- **AND** a later successful result for the same request is recorded as evidence that the earlier transport noise was not by itself a workflow failure
