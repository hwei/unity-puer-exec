## ADDED Requirements

### Requirement: Log-observation evaluation can isolate guidance failures
The repository SHALL allow targeted agent-validation analysis for tasks that depend on CLI log observation so reviewers can distinguish "the CLI lacked the needed observation surface" from "the agent did not follow the intended observation workflow."

#### Scenario: Contributor reviews a log-oriented validation run
- **WHEN** a validation task depends on log-based confirmation
- **THEN** the recorded findings can state whether the agent used `wait-for-log-pattern`, `wait-for-result-marker`, or a host-side fallback path
- **AND** the analysis can treat host-side fallback as distinct evidence rather than as invisible success
