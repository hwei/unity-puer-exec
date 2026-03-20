## Why

Project-scoped blocker detection now makes Unity save-scene dialogs visible, but operators still have to switch context and dismiss those dialogs manually. That leaves a gap between machine-usable diagnosis and machine-assisted recovery for the specific blockers that the CLI already recognizes reliably.

The next safe step is not full UI automation. It is a narrow blocker-resolution command that can cancel the supported save-scene dialogs on Windows, then hand control back to the caller to continue waiting on the original exec request.

## What Changes

- Define a dedicated blocker-resolution command for project-scoped Windows workflows.
- Define the first supported blocker actions as `cancel` for the two already-detected save-scene dialogs.
- Define the post-resolution caller flow so blocked exec requests continue through `wait-for-exec` instead of being resubmitted.
- Define real-host validation expectations for dismissing supported modal blockers and confirming the dialog closes.

## Capabilities

### New Capabilities
- `formal-cli-contract`: callers can request targeted resolution of supported Unity Editor modal blockers with `resolve-blocker`.

### Modified Capabilities
- `validation-host-integration`: real-host validation can reproduce supported modal blockers, resolve them through the CLI, and continue observing the original blocked exec flow.

## Impact

- Affects the Python CLI/session/runtime layer for project-scoped Windows workflows.
- Reuses host-side Win32 dialog inspection and adds targeted button interaction.
- Keeps responsibility boundaries clear: `resolve-blocker` dismisses the dialog, while the caller decides whether to continue `wait-for-exec` or inspect blocker state again.
