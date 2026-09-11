# compile-wait Specification

## Purpose
TBD - created by archiving change compile-loop-tooling. Update Purpose after archive.

## Requirements

### Requirement: CLI exposes an edge-aware wait-for-compile command

The CLI SHALL expose a `wait-for-compile` command accepting the standard `--project-path`/`--base-url` selectors and bounded timeout controls. The command SHALL bracket a single Unity compilation cycle by first waiting, within a bounded appear window, for the Editor to report `compiling` (or detecting that a compilation is already in progress), and then waiting for the Editor to return to `ready`. The command SHALL NOT treat an initial `ready` observation as terminal before a compile edge has been observed, so that a recompile triggered immediately before the call is not missed due to asynchronous compile start.

#### Scenario: Compile starts asynchronously after a refresh

- **WHEN** a caller triggers a recompile and then invokes `wait-for-compile`
- **AND** the Editor still reports `ready` at the first poll because compilation has not yet started
- **THEN** the command does not report completion on that initial `ready`
- **AND** it continues polling until `compiling` appears and then returns to `ready`

#### Scenario: Compilation already in progress

- **WHEN** `wait-for-compile` is invoked while the Editor already reports `compiling`
- **THEN** the command proceeds directly to waiting for the return to `ready`
- **AND** it reports completion once the Editor is `ready` again

#### Scenario: No compilation occurs within the appear window

- **WHEN** `wait-for-compile` is invoked and no `compiling` state appears within the bounded appear window and none is already in progress
- **THEN** the command returns a distinct non-error outcome indicating that no compilation was observed
- **AND** that outcome is distinguishable from a completed compile cycle so the caller can choose to retry or proceed

#### Scenario: Compilation does not finish within the settle timeout

- **WHEN** `wait-for-compile` observes a compile cycle that does not return to `ready` before the settle timeout elapses
- **THEN** the command returns a non-terminal running/timeout result rather than falsely reporting completion

### Requirement: Wait-for-compile works across both selector modes without a new server endpoint

The `wait-for-compile` command SHALL operate over the existing `/health` status signal and SHALL function in both `--project-path` and `--base-url` selector modes. In base-url mode it SHALL poll the caller-supplied endpoint directly without project-identity validation or launch ownership. The command SHALL NOT require a dedicated Unity server endpoint beyond the existing health status.

#### Scenario: Base-url caller waits for compile

- **WHEN** a caller invokes `wait-for-compile --base-url <url>`
- **THEN** the command polls that endpoint's `/health` status directly
- **AND** it does not perform project-identity validation or launch ownership for that endpoint

#### Scenario: Project-path caller waits for compile

- **WHEN** a caller invokes `wait-for-compile --project-path <path>`
- **THEN** the command resolves the project's control endpoint through the normal project-scoped discovery path
- **AND** it brackets the compile cycle using the same edge-aware logic

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
