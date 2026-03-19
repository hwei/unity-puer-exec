## MODIFIED Requirements

### Requirement: Validation records success, autonomy, and efficiency separately

The repository SHALL record task outcome, allowed-surface compliance, and convergence quality as distinct findings so discoverability problems can be diagnosed without collapsing all failures into one score. Each recorded task result SHALL also retain durable transcript evidence that includes the task prompt, the help surface consulted, the key command sequence, and the key outputs used to judge the result.

#### Scenario: Contributor records a task result
- **WHEN** a help-only validation task finishes
- **THEN** the recorded result includes whether the intended Unity-side outcome was achieved
- **AND** the recorded result includes whether the agent stayed within the allowed discovery boundary
- **AND** the recorded result includes an efficiency assessment that distinguishes clean convergence from recoverable or poor trial-and-error
- **AND** the recorded result retains durable transcript evidence for later review

## ADDED Requirements

### Requirement: Validation transcript records preserve key agent behavior
The repository SHALL define a minimum transcript record for each help-only agent validation run so later reviewers can reconstruct how the agent discovered and used the CLI.

#### Scenario: Contributor stores transcript evidence for a validation run
- **WHEN** a help-only validation run is recorded
- **THEN** the stored evidence includes the task prompt or prompt identifier
- **AND** the stored evidence includes the model or agent label used for the run
- **AND** the stored evidence includes the discovery constraints that applied to the run
- **AND** the stored evidence includes the key help commands consulted by the agent
- **AND** the stored evidence includes the key CLI command sequence and the outputs that justified the recorded outcome
- **AND** the stored evidence includes distinct result fields for task success, autonomy, and efficiency
- **AND** the stored evidence includes concrete discoverability findings for later follow-up work

### Requirement: Validation transcript records explicit operator observations
The repository SHALL record operator-observed intervention and Unity-native modal blockers separately from the agent command trace so reviewers can distinguish discoverability issues from external interference.

#### Scenario: Contributor records a run affected by observation or intervention
- **WHEN** a help-only validation run is recorded
- **THEN** the transcript record includes whether the operator only observed the run or performed non-decisive or decisive intervention
- **AND** the transcript record includes whether a Unity-native modal blocker was observed
- **AND** the transcript record identifies how the blocker was detected and how it was resolved when known

### Requirement: Validation transcript storage separates durable summaries from transient raw logs
The repository SHALL allow long raw transcript logs to live outside OpenSpec while still requiring a durable structured record that remains useful after temporary logs expire.

#### Scenario: Contributor stores transcript artifacts for a validation run
- **WHEN** a help-only validation run is recorded
- **THEN** the durable change or spec-owned record preserves the minimum structured transcript fields
- **AND** long raw logs may be stored under `.tmp/agent-validation-transcripts/`
- **AND** the durable record points to any retained raw transcript location when such evidence exists
