## MODIFIED Requirements

### Requirement: Wait-for-exec continues an accepted request by request identity

The formal CLI SHALL provide a dedicated `wait-for-exec` follow-up surface that continues or queries an accepted request by `request_id` without resubmitting script content. For project-scoped accepted requests that depend on a local pending artifact, the CLI SHALL treat that artifact as bounded local recovery state rather than as durable unbounded storage.

#### Scenario: Caller follows up on a running request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R`
- **THEN** the command reports the current known state of `R` using `running`, `completed`, or `failed`
- **AND** the caller does not need to resend the original script body

#### Scenario: Caller follows up on a missing request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R` and the addressed service has no recoverable record for `R`
- **THEN** the command returns a machine-readable `missing` result
- **AND** the contract does not require the service to distinguish whether `R` was never accepted, was lost with a replaced service instance, aged out of retention, or was represented only by a malformed local leftover

## ADDED Requirements

### Requirement: Pending exec artifacts use explicit bounded lifecycle rules

For project-scoped accepted `exec` requests that require a local pending artifact, the formal CLI SHALL persist explicit lifecycle metadata, keep the artifact only for a bounded recovery window, and remove the artifact once the request reaches a non-recoverable terminal outcome.

#### Scenario: Recoverable project-scoped request refreshes artifact metadata

- **WHEN** project-scoped `exec` or `wait-for-exec` keeps the same accepted request in a recoverable non-terminal state such as startup recovery, refreshing, compiling, or executing
- **THEN** the persisted pending artifact carries explicit creation and update timestamps
- **AND** the CLI refreshes the artifact metadata while the request remains recoverable

#### Scenario: Terminal completion removes the pending artifact

- **WHEN** the accepted project-scoped request reaches a successful or otherwise non-recoverable terminal outcome
- **THEN** the CLI removes the corresponding pending artifact promptly
- **AND** later `wait-for-exec --request-id ...` lookups do not continue treating that artifact as recoverable state

#### Scenario: Expired or malformed local artifacts are cleaned up opportunistically

- **WHEN** project-scoped `exec` or `wait-for-exec` encounters an expired, malformed, or unsupported-schema pending artifact in the addressed project's pending directory
- **THEN** the CLI removes that local leftover opportunistically
- **AND** expired or malformed local leftovers are not treated as valid recoverable requests
