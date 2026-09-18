## ADDED Requirements

### Requirement: Unknown modal dialogs are reported with stable types

When project-scoped exec or blocker-query detection observes a blocking modal dialog that matches no catalog entry, the machine-readable payload SHALL use `status = "modal_blocked"` and `blocker.type` SHALL be `unknown_modal_dialog`. The payload SHALL include the dialog window handle, title, body text, and a `buttons` array of clickable push buttons. The payload SHALL NOT include a `known` field or a `default_button` field.

#### Scenario: Unknown modal dialog is reported with stable type

- **WHEN** project-scoped exec or blocker-query detection observes a blocking modal dialog with no catalog entry
- **THEN** the machine-readable payload uses `status = "modal_blocked"`
- **AND** `blocker.type` is `unknown_modal_dialog`
- **AND** `blocker.scope` is `exec`
- **AND** the payload includes `hwnd`, `title`, `body`, and `buttons`

### Requirement: `resolve-blocker` supports explicit button-targeted resolution

The CLI SHALL support `resolve-blocker --action click --hwnd <int> --button "<label>"` for any reported modal dialog. The `hwnd` value SHALL be re-validated as a visible titled window owned by the requested project's Editor process before any control is activated; a handle failing that validation SHALL return `status = "resolution_failed"` with `error = "window_not_found"`. The `--button` value SHALL be matched against the dialog's enumerated clickable push buttons after stripping `&` mnemonics and trimming, exactly or case-insensitively; no match SHALL return `status = "resolution_failed"` with `error = "button_not_found"`. An explicit `--hwnd` target SHALL be resolved even when more than one blocking dialog is present.

#### Scenario: Caller clicks a named button on a reported dialog

- **WHEN** `resolve-blocker --project-path ... --action click --hwnd <int> --button "<label>"` is invoked with an `hwnd` from a reported blocker payload and a label that dialog carries
- **THEN** the CLI activates that button on that dialog
- **AND** success returns `status = "completed"`
- **AND** `result.status = "resolved"`
- **AND** `result.action = "click"`
- **AND** `result.blocker.type` identifies the dismissed blocker

#### Scenario: Supplied handle is stale or belongs to another process

- **WHEN** `resolve-blocker --action click` is invoked with an `hwnd` that is no longer a visible titled window owned by the requested project's Editor process
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "window_not_found"`
- **AND** no control is activated

#### Scenario: Supplied button label matches no enumerated button

- **WHEN** `resolve-blocker --action click` is invoked with a `--button` value matching none of the target dialog's enumerated clickable push buttons
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "button_not_found"`
- **AND** no control is activated

#### Scenario: Click targets an explicit window despite multiple blockers

- **WHEN** `resolve-blocker --action click --hwnd <int>` is invoked and more than one blocking dialog is detected
- **THEN** the CLI resolves the named dialog
- **AND** it does not return `multiple_supported_blockers` merely because other dialogs are present

## MODIFIED Requirements

### Requirement: `resolve-blocker` dismisses supported modal blockers explicitly

The CLI SHALL expose a dedicated `resolve-blocker` command for project-scoped Windows workflows. The first version SHALL require `--project-path`. `--action cancel` SHALL be legal only for the Safe Mode dialog, where it preserves the existing "cancel == Enter Safe Mode" semantics. Every other reported modal dialog, including the save-scene dialogs and any dialog outside the catalog, SHALL be resolved through `--action click --hwnd <int> --button "<label>"` instead. The CLI SHALL reject `--action cancel` for a dialog that is not the Safe Mode dialog rather than silently substituting another action.

#### Scenario: Caller resolves a supported blocker with cancel

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked while exactly one supported blocker dialog is present
- **THEN** the CLI attempts the targeted cancel action for that dialog
- **AND** success returns `status = "completed"`
- **AND** `result.status = "resolved"`
- **AND** `result.action = "cancel"`
- **AND** `result.blocker.type` identifies the dismissed blocker

#### Scenario: Caller cancels the Safe Mode dialog

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked while the "Enter Safe Mode?" dialog is present
- **THEN** the CLI dismisses it through the keyboard Enter path
- **AND** success returns `result.status = "resolved"` with `result.action = "cancel"`

#### Scenario: Caller attempts cancel on a save-scene dialog

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked while the detected blocker is a save-scene dialog
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "action_not_supported_for_blocker"`
- **AND** it does not activate any control on the dialog

#### Scenario: Caller invokes resolution when no supported blocker is present

- **WHEN** `resolve-blocker --project-path ...` is invoked and no supported blocker dialog is currently detected
- **THEN** the CLI returns `status = "no_supported_blocker"`
- **AND** it does not perform a fallback UI action against unrelated windows

#### Scenario: Caller invokes resolution when multiple supported blockers are present

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked and more than one supported blocker dialog is detected
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "multiple_supported_blockers"`
- **AND** it does not act on any of the matching dialogs

#### Scenario: Caller invokes resolution on an unsupported surface

- **WHEN** `resolve-blocker` is invoked without `--project-path` or on a non-Windows platform
- **THEN** the CLI returns `status = "unsupported_operation"`
- **AND** `error = "windows_project_path_required"`

### Requirement: Resolution confirms the dialog closes before reporting success

The first version SHALL confirm the targeted dialog disappears before returning a successful resolution result. This confirmation SHALL apply to every resolution action, including button-targeted clicks, not only to cancel.

#### Scenario: Cancel action is issued but dialog disappearance is not confirmed

- **WHEN** the CLI issues the targeted `cancel` action for a supported blocker but the dialog still appears present after the fixed internal confirmation timeout
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "click_not_confirmed"`

#### Scenario: Click action is issued but dialog disappearance is not confirmed

- **WHEN** the CLI issues a targeted `click` action on a named button but the dialog still appears present after the fixed internal confirmation timeout
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "click_not_confirmed"`

### Requirement: Resolution preserves blocked exec ownership

Resolving a blocker SHALL NOT resubmit or replace the original blocked exec request. The caller SHALL continue waiting on the original request if it still wants the exec outcome.

#### Scenario: Caller resolves a blocker for a blocked exec request

- **WHEN** `resolve-blocker --action cancel` succeeds for a blocker that interrupted an existing exec request
- **THEN** the CLI does not submit a new exec request automatically
- **AND** the caller can continue with `wait-for-exec --request-id ...`

#### Scenario: Caller resolves a blocker by click for a blocked exec request

- **WHEN** `resolve-blocker --action click` succeeds for a blocker that interrupted an existing exec request
- **THEN** the CLI does not submit a new exec request automatically
- **AND** the caller can continue with `wait-for-exec --request-id ...`

### Requirement: ScriptUpdater consent is recovered without a new public command

Project-scoped `exec`, `wait-for-exec`, and session-prep waits SHALL auto-decline the ScriptUpdater consent dialog using the same recovery as `wait-for-compile`. The public command tree SHALL NOT gain a new command for this dialog. `resolve-blocker --action cancel` remains defined only for the Safe Mode dialog; every other reported dialog, including the save-scene dialogs, is resolved through `resolve-blocker --action click --hwnd --button`.

#### Scenario: Session boot is blocked by ScriptUpdater consent

- **WHEN** a project-scoped command is waiting for the Editor to become ready
- **AND** the ScriptUpdater consent dialog is visible for that Editor
- **THEN** the CLI declines the dialog
- **AND** the wait continues until ready or the existing session timeout

#### Scenario: Help documents the warning without a new command

- **WHEN** a caller reads `wait-for-compile --help` or `exec --help`
- **THEN** the help text states that the ScriptUpdater consent dialog is auto-declined
- **AND** it states that `warning = "api_updater_declined"` appears on the in-flight command when a decline happened
