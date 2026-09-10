## ADDED Requirements

### Requirement: ScriptUpdater consent is recovered without a new public command

Project-scoped `exec`, `wait-for-exec`, and session-prep waits SHALL auto-decline the ScriptUpdater consent dialog using the same recovery as `wait-for-compile`. The public command tree SHALL NOT gain a new command for this dialog. `resolve-blocker --action cancel` remains defined only for the existing supported save-scene and Safe Mode dialogs.

#### Scenario: Session boot is blocked by ScriptUpdater consent

- **WHEN** a project-scoped command is waiting for the Editor to become ready
- **AND** the ScriptUpdater consent dialog is visible for that Editor
- **THEN** the CLI declines the dialog
- **AND** the wait continues until ready or the existing session timeout

#### Scenario: Help documents the warning without a new command

- **WHEN** a caller reads `wait-for-compile --help` or `exec --help`
- **THEN** the help text states that the ScriptUpdater consent dialog is auto-declined
- **AND** it states that `warning = "api_updater_declined"` appears on the in-flight command when a decline happened
