## ADDED Requirements

### Requirement: Real-host validation tolerates transient cold-launch failures

Real-host validation SHALL treat a bounded number of transient cold-launch failures as retryable rather than failing a case on the first attempt. A transient failure is one in which the CLI cannot bring the host Editor up for the case (`unity_start_failed`, or the launched Editor exits before becoming ready) while the clean-boundary check otherwise passes. Non-launch failures and genuine assertion failures SHALL NOT be retried. Every attempt SHALL be recorded with enough state to distinguish a flake from a persistent launch regression.

#### Scenario: A cold launch races the previous Editor shutdown

- **WHEN** a real-host case force-stops the host and the next launch begins before the prior Editor has fully released the project
- **THEN** the suite retries the launch within a bounded budget after confirming the boundary is clean
- **AND** a launch that succeeds on retry does not fail the case

#### Scenario: A persistent regression is not masked

- **WHEN** every launch attempt fails
- **THEN** the case fails with the attempt count and last launch status recorded
- **AND** the failure is not reported as a transient flake

#### Scenario: Non-launch failures are not retried

- **WHEN** a real-host case fails for a reason other than bringing the host up (for example an assertion on a completed CLI response)
- **THEN** the suite does not retry the case
- **AND** the original failure is reported directly
