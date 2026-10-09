## Purpose

Lets an agent move the Unity Editor between edit mode, play mode and pause with first-class commands that complete the transition, keep compiled code current around it, and keep the game loop running while the Editor is unfocused.

## ADDED Requirements

### Requirement: Play-mode commands complete the requested transition

The CLI SHALL provide `play`, `pause`, and `stop` commands that accept the standard `--project-path` / `--base-url` selectors. Each command SHALL return success only after the Editor reports the requested play state, and SHALL report the final play state in its result. When the transition does not finish within the command's budget, it SHALL return a non-terminal `running` result that names the current play state.

#### Scenario: Agent enters play mode

- **WHEN** an agent runs `play` against an Editor in edit mode
- **THEN** the command returns `status: "completed"` only after the Editor reports `playing`
- **AND** the result reports `play_state: "playing"` and `transition: "performed"`

#### Scenario: Agent pauses a playing Editor

- **WHEN** an agent runs `pause` against an Editor in play mode
- **THEN** the command returns after the Editor reports `paused`
- **AND** the result reports `play_state: "paused"`

#### Scenario: Agent leaves play mode

- **WHEN** an agent runs `stop` against an Editor in play or pause
- **THEN** the command returns after the Editor reports `edit`
- **AND** the result reports `play_state: "edit"`

#### Scenario: Transition outlasts the budget

- **WHEN** the requested transition has not finished when the command's timeout elapses
- **THEN** the command returns `status: "running"` with the current play state
- **AND** its `next_steps` re-run the same command to continue waiting

### Requirement: Play-mode commands are idempotent

Each play-mode command SHALL succeed without performing a transition when the Editor is already in the requested state, and SHALL report that no transition was needed. `play` SHALL resume a paused Editor. `pause` SHALL be rejected with a machine-readable non-success status when the Editor is in edit mode.

#### Scenario: Editor already in the requested state

- **WHEN** an agent runs `play` while the Editor is `playing`
- **THEN** the command returns `status: "completed"` with `transition: "already_in_state"`

#### Scenario: Play resumes a paused Editor

- **WHEN** an agent runs `play` while the Editor is `paused`
- **THEN** the Editor resumes and the command reports `play_state: "playing"` with `transition: "resumed"`

#### Scenario: Pause from edit mode is rejected

- **WHEN** an agent runs `pause` while the Editor is in `edit`
- **THEN** the command returns a non-success status naming the current play state
- **AND** its `next_steps` suggest `play` first

### Requirement: Play settles pending code before entering play mode

When a compile-triggering change is pending, `play` SHALL refresh and settle the compile cycle before entering play mode, so a play session never starts on code that omits a pending change. If compilation fails, `play` SHALL NOT enter play mode and SHALL return the `unity_compile_error` status and exit code that `exec` uses.

#### Scenario: Pending change compiles cleanly

- **WHEN** an agent runs `play` with a compile-triggering change pending
- **THEN** the command refreshes and waits for compilation to settle before requesting play mode
- **AND** the result discloses that a refresh ran

#### Scenario: Pending change fails to compile

- **WHEN** an agent runs `play` and the pending change has compile errors
- **THEN** the Editor stays in edit mode
- **AND** the command returns `unity_compile_error` with exit code 23 and inline compile errors

### Requirement: Stop settles the compile cycle deferred by play mode

When a compile-triggering change is pending as `stop` leaves play mode, `stop` SHALL wait, on a compile-scale budget, for the compile cycle that follows the exit, and SHALL report its outcome. A compile failure SHALL NOT make the play-mode transition itself fail. It SHALL be reported in the result, with a follow-up to read the errors.

#### Scenario: Stop with a pending change

- **WHEN** an agent runs `stop` while a compile-triggering change is pending
- **THEN** the command returns after the Editor is in `edit` and the compile cycle has settled
- **AND** the result reports the compile outcome

#### Scenario: Deferred compile fails after stop

- **WHEN** the compile cycle after `stop` reports errors
- **THEN** the command reports `play_state: "edit"` and a failed compile outcome
- **AND** its `next_steps` include `get-compile-errors`

#### Scenario: Stop with nothing pending

- **WHEN** an agent runs `stop` while no compile-triggering change is pending
- **THEN** the command returns once the Editor is in `edit`, without waiting for a compile

### Requirement: Play forces run-in-background by default

`play` SHALL set `Application.runInBackground` to true for the play session it starts, SHALL NOT modify the project's Player Settings, and SHALL disclose the override in its result together with the project's own setting. The `--no-run-in-background` option SHALL leave the project's setting in effect. The disclosure SHALL name that option.

#### Scenario: Default play forces background running

- **WHEN** an agent runs `play` without options
- **THEN** `Application.runInBackground` is true once the Editor reports `playing`
- **AND** the result reports `run_in_background.forced: true` and the project setting
- **AND** the result names `--no-run-in-background` as the way to keep the project setting

#### Scenario: Agent keeps the project setting

- **WHEN** an agent runs `play --no-run-in-background`
- **THEN** `Application.runInBackground` keeps the value the project configures
- **AND** the result reports `run_in_background.forced: false`

#### Scenario: Project settings stay unmodified

- **WHEN** a forced play session starts and ends
- **THEN** the project's Player Settings asset is not modified on disk

#### Scenario: Override survives a domain reload on entering play mode

- **WHEN** entering play mode reloads the script domain
- **THEN** the override is still applied once the Editor reports `playing`

### Requirement: Play-mode commands surface modal blockers

When a modal dialog prevents a play-mode transition, the command SHALL report a machine-usable blocking result in the same shape `exec` uses, rather than timing out without explanation.

#### Scenario: A dialog blocks leaving play mode

- **WHEN** a modal dialog appears while `stop` waits for the Editor to reach `edit`
- **THEN** the command reports the blocker
- **AND** its `next_steps` point to `get-blocker-state` / `resolve-blocker`
