# api-updater-recovery Specification

## MODIFIED Requirements

### Requirement: API Updater consent dialog is auto-declined

When the CLI observes a Unity-owned Windows dialog whose message body contains the ScriptUpdater consent text (matching either `Some of this project's source files refer to API that has changed`, `Some of this projects source files refer to API that has changed`, or the invariant core substring `source files refer to API that has changed`), it SHALL dismiss that dialog by activating the No button. It SHALL NOT activate the Yes button. After a confirmed dismiss, the CLI SHALL continue the original wait or request instead of treating the dismiss as completion. If the same dialog reappears before the current timeout budget expires, the CLI SHALL decline it again.

#### Scenario: Consent dialog appears during a compile wait

- **WHEN** a project-scoped or base-url wait is polling Unity and the ScriptUpdater consent dialog is visible for that Editor process
- **THEN** the CLI clicks No and confirms the window is gone
- **AND** the wait continues until the Editor is ready or the existing timeout expires

#### Scenario: Consent dialog reappears in the same compile cycle

- **WHEN** the CLI has already declined the ScriptUpdater consent dialog during a wait
- **AND** Unity shows the same dialog again before that wait's timeout expires
- **THEN** the CLI declines it again
- **AND** the wait still does not report completion solely because a dialog was dismissed

#### Scenario: Yes is never the recovery action

- **WHEN** the CLI dismisses the ScriptUpdater consent dialog
- **THEN** the activated control is the No button
- **AND** the CLI does not send Enter as the dismissal method for this dialog
