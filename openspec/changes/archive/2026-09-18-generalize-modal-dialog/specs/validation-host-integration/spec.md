## MODIFIED Requirements

### Requirement: Real-host validation can resolve supported modal blockers

The repository SHALL maintain real-host validation coverage for resolving the reported Unity modal blockers through the CLI. Save-scene dialogs SHALL be resolved through the explicit button-targeted path (`resolve-blocker --action click --hwnd <int> --button "<label>"`) rather than through `--action cancel`, so the validation never demonstrates a default that discards unsaved scene work. The `hwnd` passed to the command SHALL be read from the observed blocker payload. Resolution through `--action cancel` remains validated only for the Safe Mode dialog.

#### Scenario: Contributor resolves the modified-scenes prompt through the CLI

- **WHEN** the real-host validation workflow triggers the `Scene(s) Have Been Modified` dialog and then invokes `resolve-blocker --action click --hwnd <int> --button "Cancel"`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_modified_scenes_prompt"`
- **AND** follow-up observation can continue through `wait-for-exec` on the original request

#### Scenario: Contributor resolves the save-scene dialog through the CLI

- **WHEN** the real-host validation workflow triggers the `Save Scene` dialog and then invokes `resolve-blocker --action click --hwnd <int> --button "Cancel"`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_scene_dialog"`
- **AND** the workflow confirms the dialog is no longer present before treating the resolution as successful

#### Scenario: Cancel is rejected for a save-scene dialog

- **WHEN** the real-host validation workflow triggers a save-scene dialog and then invokes `resolve-blocker --action cancel`
- **THEN** the CLI reports `status = "resolution_failed"`
- **AND** `error = "action_not_supported_for_blocker"`
- **AND** the dialog remains present with unsaved scene changes intact

## ADDED Requirements

### Requirement: Real-host validation can resolve a modal dialog outside the catalog

The repository SHALL maintain real-host validation coverage for a Unity modal dialog that has no catalog entry, covering both its reporting and its resolution through the explicit button-targeted path. The validation SHALL record whether owner-based modal discrimination correctly excluded non-blocking Editor windows present at the same time.

#### Scenario: Contributor validates an unknown modal dialog

- **WHEN** the real-host validation workflow triggers a Unity modal dialog that matches no catalog entry
- **THEN** follow-up CLI observation reports `status = "modal_blocked"`
- **AND** the observed blocker payload records `blocker.type = "unknown_modal_dialog"`
- **AND** the payload includes `hwnd`, `title`, `body`, and `buttons`

#### Scenario: Contributor resolves an unknown modal dialog through the CLI

- **WHEN** the real-host validation workflow observes an `unknown_modal_dialog` blocker and then invokes `resolve-blocker --action click --hwnd <int> --button "<label>"` with a label from that payload's `buttons`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "unknown_modal_dialog"`
- **AND** the workflow confirms the dialog is no longer present before treating the resolution as successful

#### Scenario: Non-blocking Editor windows are not reported

- **WHEN** the real-host validation workflow opens Editor windows that do not block exec, such as `Preferences` or `Project Settings`, while validation observes blockers
- **THEN** CLI observation does not report any of those windows as a modal blocker
