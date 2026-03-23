## MODIFIED Requirements

### Requirement: Validation records success, autonomy, and efficiency separately

The repository SHALL record task outcome, allowed-surface compliance, and convergence quality as distinct findings so discoverability problems can be diagnosed without collapsing all failures into one score. Each recorded task result SHALL also retain durable transcript evidence that includes the task prompt, the help surface consulted, the key command sequence, and the key outputs used to judge the result. When a validation task creates repository-owned temporary assets in the external host Unity project, the recorded result SHALL also include cleanup outcome and any remaining residue.

#### Scenario: Contributor records a task result
- **WHEN** a help-only validation task finishes
- **THEN** the recorded result includes whether the intended Unity-side outcome was achieved
- **AND** the recorded result includes whether the agent stayed within the allowed discovery boundary
- **AND** the recorded result includes an efficiency assessment that distinguishes clean convergence from recoverable or poor trial-and-error
- **AND** the recorded result retains durable transcript evidence for later review
- **AND** the recorded result includes cleanup status for any repository-owned temporary host assets created by the run

### Requirement: Validation transcript records preserve key agent behavior
The repository SHALL define a minimum transcript record for each help-only agent validation run so later reviewers can reconstruct how the agent discovered and used the CLI.

#### Scenario: Contributor stores transcript evidence for a validation run
- **WHEN** a help-only validation run is recorded
- **THEN** the stored evidence includes the task prompt or prompt identifier
- **AND** the stored evidence includes the model or agent label used for the run
- **AND** the stored evidence includes the discovery constraints that applied to the run
- **AND** the stored evidence includes the key help commands consulted by the agent
- **AND** the stored evidence includes the key CLI command sequence and the outputs that justified the recorded outcome
- **AND** the stored evidence includes distinct result fields for task success, autonomy, efficiency, and cleanup status
- **AND** the stored evidence includes concrete discoverability findings for later follow-up work
