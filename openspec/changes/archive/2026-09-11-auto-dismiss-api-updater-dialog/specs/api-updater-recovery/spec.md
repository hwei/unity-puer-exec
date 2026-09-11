## Purpose

Recover from Unity ScriptUpdater's blocking Yes/No consent dialog without rewriting project sources, and tell the in-flight CLI command that the rewrite was declined.

## ADDED Requirements

### Requirement: API Updater consent dialog is auto-declined

When the CLI observes a Unity-owned Windows dialog whose message body contains the ScriptUpdater consent text (`Some of this project's source files refer to API that has changed`), it SHALL dismiss that dialog by activating the No button. It SHALL NOT activate the Yes button. After a confirmed dismiss, the CLI SHALL continue the original wait or request instead of treating the dismiss as completion. If the same dialog reappears before the current timeout budget expires, the CLI SHALL decline it again.

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

### Requirement: In-flight command carries api_updater_declined warning

When a CLI command dismisses the ScriptUpdater consent dialog at least once during that invocation, the command's machine-readable response SHALL include `warning` set to `api_updater_declined` and a human-readable `warning_detail` stating that Unity offered to rewrite sources for changed APIs, that the CLI declined, and that compile errors or `(UnityUpgradable)` messages may remain. The command's primary `status` and exit code SHALL follow the command's existing contract. This warning SHALL NOT use `status: "warning"` unless that was already the command's primary status.

#### Scenario: wait-for-compile settles after a decline

- **WHEN** `wait-for-compile` declines the ScriptUpdater consent dialog and the Editor then returns to ready
- **THEN** the command reports the normal compile-settled success outcome
- **AND** the payload includes `warning = "api_updater_declined"`
- **AND** the process exit code remains the success exit for a settled compile

#### Scenario: exec completes after a decline during refresh or wait

- **WHEN** `exec` or `wait-for-exec` declines the ScriptUpdater consent dialog while preparing or waiting
- **AND** the script later completes successfully
- **THEN** the payload keeps `status = "completed"`
- **AND** the payload includes `warning = "api_updater_declined"`

#### Scenario: compile still fails after a decline

- **WHEN** a command declines the ScriptUpdater consent dialog
- **AND** C# compilation still has errors
- **THEN** the command still reports `unity_compile_error` (or the existing compile-error outcome for that command)
- **AND** the payload also includes `warning = "api_updater_declined"`

#### Scenario: command that did not dismiss omits the warning

- **WHEN** a command finishes without dismissing the ScriptUpdater consent dialog
- **THEN** the payload does not include `warning = "api_updater_declined"`

### Requirement: Agents never see this dialog as modal_blocked

The ScriptUpdater consent dialog SHALL NOT be surfaced as `status = "modal_blocked"` and SHALL NOT require `resolve-blocker`. Save-scene dialogs keep their existing `modal_blocked` contract.

#### Scenario: exec timeout coincides with the consent dialog

- **WHEN** `exec` or `wait-for-exec` would otherwise inspect modal blockers because the request is running or timed out
- **AND** the only supported dialog is the ScriptUpdater consent dialog
- **THEN** the CLI auto-declines it
- **AND** the response is not `modal_blocked` with an API-updater blocker type

### Requirement: CLI-owned launches disable AssemblyUpdater without replacing ScriptUpdater recovery

A Unity process launched by this CLI SHALL include the `-disable-assembly-updater` argument with no assembly-name parameters, unless that exact switch is already present in the merged launch argv. The CLI SHALL still perform ScriptUpdater consent-dialog recovery, because that switch does not stop ScriptUpdater in an interactive Editor. The Editor.log line that reports ignored assemblies SHALL NOT by itself produce `warning = "api_updater_declined"`.

#### Scenario: Cold launch injects the assembly-updater switch

- **WHEN** the CLI cold-starts Unity for a project it owns
- **THEN** the launched argv includes `-disable-assembly-updater`
- **AND** a later ScriptUpdater consent dialog for that process is still auto-declined and still produces `api_updater_declined` when clicked

#### Scenario: Caller already passed the switch

- **WHEN** ambient or `--unity-launch-arg` tokens already include `-disable-assembly-updater`
- **THEN** the CLI does not fail the launch as a reserved-switch conflict
- **AND** the launched argv still contains the switch once

#### Scenario: Ignoring-assembly log is not the warning

- **WHEN** Editor.log contains `[Assembly Updater] warning: Ignoring assembly` because the launch switch is present
- **AND** the ScriptUpdater consent dialog was not dismissed in this command
- **THEN** the command payload does not include `warning = "api_updater_declined"`
