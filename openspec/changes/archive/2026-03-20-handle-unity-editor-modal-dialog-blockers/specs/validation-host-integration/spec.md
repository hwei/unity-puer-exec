## ADDED Requirements

### Requirement: Real-host validation can reproduce and record modal dialog blockers
The repository SHALL maintain a repeatable real-host validation expectation for at least one Unity-native modal dialog blocker scenario so contributors can distinguish CLI contract regressions from editor-side blocking behavior.

#### Scenario: Contributor validates a save-scene modal blocker path
- **WHEN** a contributor runs the repository-owned real-host validation workflow for a scenario that triggers a Unity-native save-scene modal dialog
- **THEN** the workflow records whether the CLI exposed a machine-usable blocker outcome or blocker diagnostics
- **AND** the workflow does not treat a manual operator click-through as equivalent to normal unattended success

#### Scenario: Contributor validates the untitled-scene save dialog path
- **WHEN** the real-host validation workflow triggers a new untitled scene save request that opens the `Save Scene` file-save dialog
- **THEN** follow-up CLI observation can report `status = "modal_blocked"`
- **AND** the observed blocker payload records `blocker.type = "save_scene_dialog"`
