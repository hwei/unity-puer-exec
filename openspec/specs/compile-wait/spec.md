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

### Requirement: Wait-for-compile reports a compile blocked by play mode

When `wait-for-compile` finds no compile in progress, a compile-triggering change pending, and the Editor in play mode, it SHALL return a distinct `compile_blocked` outcome naming play mode as the reason, rather than `no_compile_observed`. The command SHALL NOT spend the full appear window waiting for a compile that cannot start. The outcome SHALL be non-terminal for the compile: it says nothing about whether the pending change compiles.

#### Scenario: Pending change while the Editor is in play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor is in play mode
- **AND** a compile-triggering change is pending
- **AND** no compile is in progress
- **THEN** the command returns `result.status: "compile_blocked"` with `compile_observed: false`
- **AND** the result names `play_mode` as the reason
- **AND** the command returns without waiting out the appear window

#### Scenario: Nothing pending while the Editor is in play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor is in play mode
- **AND** no compile-triggering change is pending
- **THEN** the command keeps its existing outcomes, including `no_compile_observed`
- **AND** it does not report `compile_blocked`

#### Scenario: Compile already in progress during play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor already reports `compiling` while in play mode
- **THEN** the command waits for that compile cycle to settle as it does outside play mode

### Requirement: Wait-for-compile accepts a compile-generation baseline

`wait-for-compile` SHALL accept an optional compile-generation baseline so that a caller which holds a value recorded before a domain reload can pass it to the command.

#### Scenario: Caller supplies a pre-reload baseline

- **WHEN** a caller records the compile generation before requesting a transition that crosses a domain reload
- **THEN** the caller can supply that value as `wait-for-compile`'s baseline

### Requirement: Wait-for-compile settles an inferred cross-reload compile from an advanced baseline

When the Editor reports a compile generation strictly greater than the supplied baseline, `wait-for-compile` SHALL report `compile_settled` with `compile_observed: true` and SHALL name the generation-advance edge. It SHALL return this outcome even when it never observed `compiling` and the endpoint was already `ready` at its first poll.

#### Scenario: Deferred play-exit compile crosses a reload

- **WHEN** `wait-for-compile` is invoked with a baseline recorded before play exit
- **AND** the Editor reports a compile generation greater than that baseline after the endpoint returns
- **THEN** the command reports `compile_settled` with `compile_observed: true`
- **AND** the result names the generation-advance edge
- **AND** it does not report `no_compile_observed`

### Requirement: Wait-for-compile never infers a settle without an advanced baseline

`wait-for-compile` SHALL keep its existing outcomes when no baseline is supplied or the baseline has not advanced. A caller that starts after the reload without a baseline SHALL receive `no_compile_observed`, not `compile_settled`.

#### Scenario: No baseline is supplied after the reload

- **WHEN** `wait-for-compile` is invoked after a reload without a compile-generation baseline
- **AND** the Editor is `ready` with no compile in progress
- **THEN** the command keeps its existing `no_compile_observed` outcome

#### Scenario: Supplied baseline is already current

- **WHEN** `wait-for-compile` is invoked with a baseline equal to the current compile generation
- **AND** no compilation completes within the appear window
- **THEN** the command reports `no_compile_observed`
