## ADDED Requirements

### Requirement: Real-host validation can reproduce and record modal dialog blockers
The repository SHALL maintain a repeatable real-host validation expectation for at least one Unity-native modal dialog blocker scenario so contributors can distinguish CLI contract regressions from editor-side blocking behavior.

#### Scenario: Contributor validates a save-scene modal blocker path
- **WHEN** a contributor runs the repository-owned real-host validation workflow for a scenario that triggers a Unity-native save-scene modal dialog
- **THEN** the workflow records whether the CLI exposed a machine-usable blocker outcome or blocker diagnostics
- **AND** the workflow does not treat a manual operator click-through as equivalent to normal unattended success
