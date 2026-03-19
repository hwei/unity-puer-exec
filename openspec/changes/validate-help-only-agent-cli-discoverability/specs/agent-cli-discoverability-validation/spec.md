## ADDED Requirements

### Requirement: Help-only agent validation uses published CLI discovery surfaces
The repository SHALL define a repeatable validation protocol for agent CLI discoverability that restricts the primary discovery surface to the publishable `unity-puer-exec` help interface and normal CLI execution.

#### Scenario: Contributor prepares a help-only agent trial
- **WHEN** a contributor runs the repository-owned agent discoverability validation
- **THEN** the protocol allows `unity-puer-exec --help`, command help, `--help-args`, `--help-status`, `--help-example`, and normal CLI execution
- **AND** the protocol does not rely on repository-only source or repository tests as part of the allowed discovery surface

### Requirement: First-round validation covers both simple and multi-step Unity Editor tasks
The repository SHALL define an initial task set that exercises both direct Unity Editor action and a longer workflow that includes code change, compile or readiness recovery, and outcome verification.

#### Scenario: Contributor reviews the first-round task set
- **WHEN** the first-round help-only validation tasks are defined
- **THEN** the task set includes at least one simple Unity Editor action task
- **AND** the task set includes at least one longer workflow task that requires the agent to complete a code change and verify the result in the real editor context

### Requirement: Validation records success, autonomy, and efficiency separately
The repository SHALL record task outcome, allowed-surface compliance, and convergence quality as distinct findings so discoverability problems can be diagnosed without collapsing all failures into one score.

#### Scenario: Contributor records a task result
- **WHEN** a help-only validation task finishes
- **THEN** the recorded result includes whether the intended Unity-side outcome was achieved
- **AND** the recorded result includes whether the agent stayed within the allowed discovery boundary
- **AND** the recorded result includes an efficiency assessment that distinguishes clean convergence from recoverable or poor trial-and-error

### Requirement: Validation findings isolate discoverability gaps
The repository SHALL capture concrete discoverability findings from each help-only trial in a form that can drive later product, workflow, or harness follow-up work.

#### Scenario: Contributor summarizes a help-only trial
- **WHEN** a help-only agent validation run is reviewed
- **THEN** the summary identifies the help or workflow gaps that materially slowed or blocked the task
- **AND** the summary distinguishes those discoverability findings from unrelated runtime or environment failures
