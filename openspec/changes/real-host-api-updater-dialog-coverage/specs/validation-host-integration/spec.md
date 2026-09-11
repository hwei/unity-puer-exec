## ADDED Requirements

### Requirement: Real-host validation covers ScriptUpdater consent-dialog recovery

The repository SHALL maintain a repeatable real-host validation expectation for the ScriptUpdater consent-dialog recovery path, so the Win32 matcher, the No-button click, and the `warning = "api_updater_declined"` propagation are exercised against a real Unity dialog rather than mocks only. The validation SHALL use a repository-owned host fixture to make Unity show the dialog and SHALL leave the host clean afterwards. When the dialog cannot be produced deterministically for the current host or Unity version, the case SHALL skip with a machine-usable diagnosed reason instead of reporting a vacuous pass.

#### Scenario: Contributor validates consent-dialog auto-decline against a real host

- **WHEN** the real-host validation makes the validation host Editor show the ScriptUpdater consent dialog and then runs a CLI wait or exec
- **THEN** the CLI auto-declines the dialog and the command keeps its primary status while also reporting `warning = "api_updater_declined"`
- **AND** the workflow confirms the dialog is gone and project source files were not rewritten (declined, not accepted)

#### Scenario: Consent dialog cannot be triggered on the current host

- **WHEN** the real-host validation cannot make the validation host Editor show the ScriptUpdater consent dialog
- **THEN** the case skips with a diagnosed reason that names the trigger blocker
- **AND** it does not report a pass that would be indistinguishable from a genuine recovery verification

#### Scenario: Non-English dialog text is recorded

- **WHEN** the validation host Editor shows the consent dialog with message text that does not match the English fingerprint
- **THEN** the validation records the observed message text
- **AND** it does not silently report the recovery as verified
