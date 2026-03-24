## ADDED Requirements

### Requirement: Ordinary log-workflow guidance is validated against transcript-backed reruns
The repository SHALL evaluate ordinary log-workflow help changes with a clean help-only rerun of the representative log-oriented baseline so the effect of the published workflow example can be judged against prior transcript-backed evidence.

#### Scenario: Contributor reruns the representative log-oriented baseline
- **WHEN** a contributor validates a help-surface change that adds or revises the ordinary log workflow example
- **THEN** the contributor runs a help-only trial that reuses the representative log-oriented baseline rather than relying only on unit tests or implementation-session notes
- **AND** the resulting record compares the rerun against earlier transcript-backed Prompt B style evidence

### Requirement: Ordinary log-workflow reruns record final verification path explicitly
The repository SHALL record whether a representative log-oriented rerun kept final confirmation inside the CLI observation surface or fell back to direct host-log inspection.

#### Scenario: Contributor records the rerun outcome
- **WHEN** the representative log-oriented help-only rerun finishes
- **THEN** the durable record states whether final confirmation used the intended CLI observation path
- **AND** the durable record states whether direct host-log inspection was still used for final verification
- **AND** those findings are recorded separately from unrelated compile recovery or startup friction

### Requirement: Ordinary log-workflow reruns record checkpoint usage explicitly
The repository SHALL record whether a representative log-oriented rerun used the intended observation checkpoint pattern when validating ordinary log-workflow guidance.

#### Scenario: Contributor summarizes checkpoint usage
- **WHEN** a contributor reviews a representative log-oriented help-only rerun after the ordinary log workflow example change
- **THEN** the durable record states whether the run captured `log_offset` before calling `wait-for-log-pattern`
- **AND** the durable record states whether `wait-for-log-pattern` started from the returned checkpoint
- **AND** the durable record distinguishes checkpoint-usage findings from unrelated runtime or environment issues
