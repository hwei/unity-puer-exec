## ADDED Requirements

### Requirement: Wait-for-compile auto-declines ScriptUpdater consent during appear and settle

`wait-for-compile` SHALL poll for the ScriptUpdater consent dialog while waiting for `compiling` to appear and while waiting for `ready`. When that dialog is present for the Editor process being waited on, the command SHALL auto-decline it and continue the same compile-edge wait. A decline SHALL NOT by itself produce `compile_settled` or `no_compile_observed`.

#### Scenario: Dialog appears while health stays compiling

- **WHEN** `wait-for-compile` has observed `compiling`
- **AND** the ScriptUpdater consent dialog is visible for that Editor
- **THEN** the command declines the dialog before the settle timeout is relied on as the only recovery
- **AND** it continues polling `/health` until `ready` or the settle timeout

#### Scenario: Dialog appears before the compile edge

- **WHEN** `wait-for-compile` is still in the appear window
- **AND** the ScriptUpdater consent dialog is visible
- **THEN** the command declines the dialog
- **AND** it does not treat the current `ready` (if any) as a completed compile cycle solely because the dialog was dismissed

#### Scenario: Settled cycle reports the decline warning

- **WHEN** `wait-for-compile` declined the ScriptUpdater consent dialog at least once
- **AND** the Editor returns to `ready` after a compile edge
- **THEN** the command reports `compile_settled` with `compile_observed` true
- **AND** the payload includes `warning = "api_updater_declined"`
