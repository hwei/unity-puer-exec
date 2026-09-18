# modal-dialog-surface Specification

## Purpose
Detect and report any modal dialog that blocks the Unity Editor main thread, including dialogs the CLI has no catalog entry for, distinguish true modals from non-blocking Editor windows, and give callers an explicit button-targeted way to resolve a reported dialog.

## Requirements

### Requirement: Blocking modal dialogs are reported even when no catalog entry matches

When the CLI inspects modal blockers for a Unity Editor process, it SHALL report every window it determines to be a true modal dialog owned by that process, including windows that do not match any title-keyed or message-body-keyed catalog entry. A reported dialog outside the catalog SHALL use `blocker.type = "unknown_modal_dialog"`. The CLI SHALL NOT silently discard a window merely because no catalog entry matched it.

#### Scenario: An unrecognized modal dialog blocks exec

- **WHEN** project-scoped exec has stalled (`timed out` or `running`) and the Editor process owns a visible modal dialog whose title matches no catalog entry
- **THEN** the CLI reports `status = "modal_blocked"`
- **AND** `blocker.type` is `unknown_modal_dialog`
- **AND** `blocker.scope` is `exec`

#### Scenario: An unrecognized modal dialog is reported by the blocker query

- **WHEN** a caller invokes the blocker-query command while the Editor owns a visible modal dialog that matches no catalog entry
- **THEN** the command reports `result.status = "modal_blocked"`
- **AND** `result.blocker.type` is `unknown_modal_dialog`
- **AND** the caller is not required to resubmit the blocked exec request to learn this

### Requirement: Unknown dialog payloads carry the detail needed to decide

An `unknown_modal_dialog` blocker payload SHALL include the dialog window handle, its title, its message body text, and a `buttons` array. Each `buttons` entry SHALL carry a `label` and a `ctrl_id`. The payload SHALL NOT carry a `known` field and SHALL NOT carry a `default_button` field: `type` alone distinguishes an unknown dialog from a catalog one, and no host-independent mechanism derives a default button reliably enough to publish.

#### Scenario: Caller reads an unknown dialog payload

- **WHEN** a caller receives `blocker.type = "unknown_modal_dialog"`
- **THEN** the payload includes `hwnd`, `title`, `body`, and `buttons`
- **AND** each `buttons` entry includes `label` and `ctrl_id`
- **AND** the payload includes no `known` field and no `default_button` field

### Requirement: True modals are discriminated from non-blocking Editor windows

The CLI SHALL NOT treat visibility plus a non-empty title as sufficient evidence that a window blocks the Editor. A window SHALL be classified as a true modal when its owner window is present and disabled, or — for a dialog with no owner — when it carries dialog styling and occupies a size consistent with a modal prompt. A window that fails both tests SHALL NOT be reported as a blocker. When this discrimination is uncertain for a window, the CLI SHALL classify it as non-blocking rather than as a blocker.

#### Scenario: Settings windows are not reported as blockers

- **WHEN** the Editor process owns visible titled windows such as `Preferences`, `Project Settings`, `Build Settings`, or `About Unity`
- **AND** those windows neither disable an owner window nor present as ownerless modal dialogs
- **THEN** the CLI does not report any of them as a modal blocker

#### Scenario: An ownerless modal dialog is still reported

- **WHEN** the Editor owns a visible titled window with no owner window
- **AND** the window carries dialog styling and a size consistent with a modal prompt
- **THEN** the CLI reports it as a modal blocker

#### Scenario: Misclassification downgrades rather than promotes

- **WHEN** the CLI cannot confidently classify a visible titled Editor window as a true modal
- **THEN** the window is treated as non-blocking
- **AND** it is not promoted to a blocker on the strength of an uncertain signal

### Requirement: Unknown dialogs never receive an automatic action

The CLI SHALL NOT automatically click, dismiss, or otherwise act on a dialog reported as `unknown_modal_dialog`. Resolving an unknown dialog SHALL require an explicit caller decision naming the button to activate.

#### Scenario: Unknown dialog is not auto-dismissed during exec normalization

- **WHEN** exec normalization detects an `unknown_modal_dialog` blocker
- **THEN** the CLI reports the blocker to the caller
- **AND** the CLI does not activate any button on that dialog

### Requirement: Button enumeration exposes only clickable push buttons

When the CLI enumerates the buttons of a reported dialog, each returned entry SHALL correspond to a control that is clickable as an action. The enumeration SHALL exclude controls that are checkboxes, radio buttons, or group boxes, and SHALL exclude controls that are disabled or invisible.

#### Scenario: Checkbox and radio controls are excluded

- **WHEN** a reported dialog contains checkbox or radio controls alongside push buttons
- **THEN** the payload's `buttons` array includes only the push buttons
- **AND** no checkbox or radio control appears as a `buttons` entry

#### Scenario: Disabled controls are excluded

- **WHEN** a reported dialog contains a push button that is currently disabled
- **THEN** that button does not appear in the payload's `buttons` array

### Requirement: Button labels are matched mnemonic-insensitively

Button label matching SHALL strip `&` mnemonic markers, trim surrounding whitespace, and then match exactly or case-insensitively. A `--button` value that matches no enumerated button SHALL be reported as `error = "button_not_found"` with no action taken against the dialog.

#### Scenario: Caller supplies a label with a mnemonic marker

- **WHEN** a caller resolves a dialog whose button label is `&Save` and passes `--button "Save"`
- **THEN** the CLI matches the button
- **AND** it proceeds with the targeted click

#### Scenario: Caller supplies a label no button carries

- **WHEN** a caller passes a `--button` value that matches none of the dialog's enumerated buttons
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "button_not_found"`
- **AND** no control on the dialog is activated

### Requirement: Reported dialogs are resolved by activating a named button on a validated window

The CLI SHALL support resolving a reported modal dialog by activating a caller-named button on a caller-named window handle. Before activating anything, the CLI SHALL re-validate that the supplied handle is still a visible, titled window owned by the Editor process for the requested project. A handle that fails that validation SHALL produce `error = "window_not_found"` with no action taken.

#### Scenario: Caller clicks a named button on a reported dialog

- **WHEN** a caller invokes resolution with a click action, the `hwnd` from a reported blocker payload, and a button label that dialog carries
- **THEN** the CLI activates that button
- **AND** success is reported only after the dialog is confirmed to have disappeared

#### Scenario: Supplied handle no longer belongs to the project's Editor

- **WHEN** a caller supplies an `hwnd` that is not currently a visible titled window owned by the requested project's Editor process
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "window_not_found"`
- **AND** no control is activated

#### Scenario: Click targets an explicit window even when other dialogs are present

- **WHEN** a caller supplies an explicit `hwnd` and more than one blocking dialog is present
- **THEN** the CLI resolves the named dialog rather than refusing because several dialogs exist

### Requirement: Non-foreground click methods are preferred over focus-stealing ones

When the CLI activates a dialog button, it SHALL prefer message-level activation over activation that brings the dialog to the foreground. The CLI SHALL attempt button-message activation first, then command-message activation, then posted key messages, and SHALL fall back to foregrounding only when those do not confirm. The Safe Mode dialog SHALL remain exempt and SHALL continue to use the foreground keyboard path.

#### Scenario: Message-level activation succeeds without foregrounding

- **WHEN** the CLI activates a button on a dialog that responds to button messages
- **THEN** the CLI uses button-message activation
- **AND** it does not bring the dialog to the foreground

#### Scenario: Safe Mode keeps the keyboard path

- **WHEN** the CLI resolves the "Enter Safe Mode?" dialog
- **THEN** the CLI uses the foreground keyboard path
- **AND** it does not switch that dialog to the message-level chain

### Requirement: Unknown dialogs sort ahead of catalog dialogs

When more than one blocking dialog is detected, the CLI SHALL report the `unknown_modal_dialog` blocker ahead of catalog dialog types.

#### Scenario: Unknown and save-scene dialogs are both present

- **WHEN** the Editor owns both an unrecognized modal dialog and a catalog save-scene dialog
- **THEN** the reported blocker is the `unknown_modal_dialog`
