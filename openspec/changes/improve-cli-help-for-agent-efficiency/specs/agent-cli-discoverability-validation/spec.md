## ADDED Requirements

### Requirement: Help efficiency validation compares convergence quality across revisions
The repository SHALL treat agent-efficiency validation as a comparison problem, using transcript-backed evidence to assess whether help revisions reduce unnecessary exploration for representative tasks.

#### Scenario: Contributor evaluates a help efficiency change
- **WHEN** a contributor reruns representative help-only agent validation tasks after a help-surface change
- **THEN** the evaluation compares convergence quality against earlier transcript-backed runs
- **AND** the evaluation does not rely only on final task success as the measure of improvement
