# Spec Delta

## Purpose

Defines how the CLI closes a project's Unity Editor. It asks Unity to quit through its normal quit path first, escalates only when that fails and says so, and never steers agents toward exiting the Editor from inside a script.

## ADDED Requirements

### Requirement: ensure-closed quits the Editor gracefully before escalating

In project mode, without `--inspect-only` or `--immediate-kill`, `ensure-closed` SHALL ask the project's running Editor to quit through Unity's normal quit path. It SHALL then wait up to `--timeout-seconds` for the project to be stopped, and SHALL escalate to a kill only if the Editor is still running at the end of that wait. The result SHALL report `closed_via` as `already_stopped`, `graceful` or `killed`.

#### Scenario: Idle Editor closes gracefully

- **WHEN** an agent runs `ensure-closed --project-path P` while P's Editor is idle in edit mode with no unsaved changes
- **THEN** the Editor exits through its normal quit path within the timeout
- **AND** the result reports `status: stopped` and `closed_via: graceful`
- **AND** no process is killed

#### Scenario: Graceful quit saves project settings like a user close

- **WHEN** the in-memory project settings differ from `ProjectSettings.asset` and `ensure-closed` closes the Editor gracefully
- **THEN** the project settings are saved as they would be when a user closes the Editor window

#### Scenario: Editor that does not quit is killed and the kill is disclosed

- **WHEN** the Editor neither exits nor shows a supported modal blocker before the timeout
- **THEN** `ensure-closed` kills the project's published Editor process
- **AND** the result reports `closed_via: killed`

#### Scenario: Already stopped project

- **WHEN** the project's lockfile is not held
- **THEN** the result reports `status: stopped` and `closed_via: already_stopped`

### Requirement: A modal blocker holding the quit is reported, not killed

When a supported modal blocker appears while `ensure-closed` waits for a graceful quit, for example a prompt to save modified scenes, `ensure-closed` SHALL stop waiting, SHALL NOT kill the Editor, and SHALL report the existing modal-blocker status and exit code with guidance naming `resolve-blocker` and `--immediate-kill`.

#### Scenario: Unsaved scene prompt during close

- **WHEN** the active scene has unsaved changes and `ensure-closed` asks the Editor to quit
- **AND** the Editor shows a supported save-changes dialog
- **THEN** `ensure-closed` returns the modal-blocker status with its formal exit code
- **AND** the Editor process is still running
- **AND** `next_steps` names `resolve-blocker` for the dialog and `ensure-closed --immediate-kill` for discarding the changes

### Requirement: Help recommends ensure-closed for closing the Editor

The CLI help SHALL present `ensure-closed` as the way to close a project's Editor, SHALL NOT recommend an exec script for exiting the Editor, and SHALL state that calling `EditorApplication.Exit` from an exec script crashes the Editor.

#### Scenario: Agent looks up how to close the Editor

- **WHEN** an agent reads the top-level help or `ensure-closed --help`
- **THEN** `ensure-closed` is described as the recommended way to close the project's Editor
- **AND** neither help text recommends `exec` with an exit script
- **AND** `ensure-closed --help` warns that `EditorApplication.Exit` inside an exec script crashes the Editor

### Requirement: exec refuses a script that exits the Editor

Before submitting, `exec` SHALL refuse a script whose source calls `EditorApplication.Exit`. It SHALL NOT submit the script, and SHALL return a non-success status that names `ensure-closed` as the way to close the Editor.

#### Scenario: Exit script is refused before submission

- **WHEN** an agent runs `exec` with code or a file that calls `EditorApplication.Exit(0)`
- **THEN** nothing is submitted to the Editor
- **AND** the response is a non-success status with its formal exit code
- **AND** `next_steps` names `ensure-closed --project-path ...`

#### Scenario: Unrelated scripts are unaffected

- **WHEN** an exec script does not call `EditorApplication.Exit`
- **THEN** `exec` submits it as before
