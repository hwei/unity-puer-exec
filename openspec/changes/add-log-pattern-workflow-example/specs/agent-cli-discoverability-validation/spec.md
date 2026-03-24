## ADDED Requirements

### Requirement: Ordinary log-workflow guidance is validated against host-log fallback
The repository SHALL evaluate ordinary log-workflow help changes against transcript-backed baseline evidence that specifically records whether the agent keeps final verification inside the CLI observation surface or falls back to direct host-log inspection.

#### Scenario: Contributor evaluates an ordinary log-workflow help change
- **WHEN** a contributor reruns the representative log-oriented help-only baseline after adding or revising an ordinary log workflow example
- **THEN** the durable record states whether the agent used the intended `exec` plus `wait-for-log-pattern` path for final verification
- **AND** the durable record states whether direct host-log inspection was still used for final confirmation
- **AND** the comparison is made against earlier transcript-backed baseline evidence rather than against task success alone

### Requirement: Ordinary log-workflow validation records checkpoint usage explicitly
The repository SHALL record whether a representative log-oriented validation run used the intended observation checkpoint pattern when evaluating changes to ordinary log-workflow guidance.

#### Scenario: Contributor records a rerun after an ordinary log-workflow example change
- **WHEN** a representative log-oriented baseline run finishes after the help surface adds an ordinary log verification example
- **THEN** the durable record states whether the run captured `log_offset` before waiting on `wait-for-log-pattern`
- **AND** the durable record states whether `wait-for-log-pattern` started from the returned checkpoint or from an unbounded log scan
- **AND** those findings are recorded separately from unrelated compile-recovery or startup-continuity friction
