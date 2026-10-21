# play-mode-control Specification

## Purpose

Lets an agent move the Unity Editor between edit mode, play mode and pause with first-class commands that complete the transition, keep compiled code current around it, and keep the game loop running while the Editor is unfocused.

## Requirements

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

`stop` SHALL record the Editor's compile generation before it requests the exit. When a compile-triggering change is pending as `stop` leaves play mode, or the compile generation advances past that baseline, `stop` SHALL wait, on a compile-scale budget, for the compile cycle that follows the exit.

#### Scenario: Stop with a pending change

- **WHEN** an agent runs `stop` while a compile-triggering change is pending
- **THEN** the command returns after the Editor is in `edit` and the compile cycle has settled
- **AND** the result reports `compile.outcome: "compile_settled"` and the edge it was observed by

#### Scenario: Compile hidden behind the play-exit domain reload

- **WHEN** the deferred compile runs while the control endpoint is down for the whole compile and domain reload, so `compiling` is never observable
- **THEN** the result reports `compile.outcome: "compile_settled"` with `edge: "generation_advance"`
- **AND** it does not report `no_compile_observed`

#### Scenario: Compile without a positive pending signal

- **WHEN** the pending state reads `not_pending` but a change excluded from pending detection (for example a script deletion) compiles as the Editor leaves play mode
- **THEN** the compile generation advance is reported as `compile.outcome: "compile_settled"`

#### Scenario: Stop with nothing pending

- **WHEN** an agent runs `stop` while no compile-triggering change is pending and the compile generation does not advance during the exit
- **THEN** the command returns once the Editor is in `edit`, without waiting for a compile
- **AND** the result reports `compile.outcome: "no_compile_observed"`

### Requirement: Stop reports the deferred compile outcome

`stop` SHALL report the deferred compile in the `wait-for-compile` vocabulary
(`compile_settled` or `no_compile_observed`), together with the edge the compile was observed
by. A compile failure SHALL NOT make the play-mode transition itself fail. It SHALL be reported
as a non-zero `compile_errors_total`, with a follow-up to read the errors. When the compile-error
total cannot be read — for example the control endpoint resets or answers without a usable
body — `stop` SHALL omit `compile_errors_total` and SHALL include
`compile_error_total_available: false` rather than reporting a default `0`.

#### Scenario: Deferred compile fails after stop

- **WHEN** the compile cycle after `stop` reports errors
- **THEN** the command reports `play_state: "edit"`, `compile.outcome: "compile_settled"`, and a `compile_errors_total` greater than zero
- **AND** its `next_steps` include `get-compile-errors`

#### Scenario: Compile-error total cannot be read

- **WHEN** the compile cycle settles but the follow-up read of the compile-error total cannot be read (for example the control endpoint resets, or answers without a usable body)
- **THEN** the compile block omits `compile_errors_total`
- **AND** it includes `compile_error_total_available: false`
- **AND** the command does not report `compile_errors_total: 0` for that failed read

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

### Requirement: Play-mode commands recover a dropped control endpoint

When a play-mode request cannot be delivered because the control endpoint dropped — for
example an empty or unparseable response body during a domain reload, or a connection the
endpoint reset before answering — each play-mode command SHALL re-resolve the endpoint and
retry the request within its bound. If the endpoint does not recover within the bound, the
command SHALL report the structured non-success state that names the condition, with its
formal exit code, instead of collapsing it into a generic failure. When the drop was a
connection reset, the underlying transport detail (for example the reset errno) SHALL remain
visible in the reported payload so the condition is recognizable when it recurs.

#### Scenario: Endpoint drops mid-transition and recovers

- **WHEN** a play-mode request reaches a control endpoint that drops before answering (for example an empty response body) and the Editor's endpoint becomes reachable again within the command's budget
- **THEN** the command re-resolves the endpoint and retries the request
- **AND** it does not report the dropped response as a terminal failure

#### Scenario: Endpoint never recovers within the bound

- **WHEN** the control endpoint stays unreachable for the whole command budget
- **THEN** the command returns the structured non-success state that names the empty/unreachable condition
- **AND** the process exits with that state's formal exit code rather than a generic failure code

#### Scenario: A recognized non-success answer is not retried as a transport drop

- **WHEN** the endpoint answers with a recognized non-success play-mode status such as `invalid_play_state`
- **THEN** the command reports that status without treating it as a dropped endpoint or retrying the request

#### Scenario: Endpoint resets mid-transition and recovers

- **WHEN** a play-mode request reaches a control endpoint that accepts the connection and then resets it before sending a response, and the Editor's endpoint becomes reachable again within the command's budget
- **THEN** the command re-resolves the endpoint and retries the request
- **AND** it does not report the reset as a terminal or generic failure

#### Scenario: Endpoint keeps resetting for the whole bound

- **WHEN** the control endpoint resets every attempt for the whole command budget
- **THEN** the process exits with the formal exit code for the not-available condition rather than a generic failure code
- **AND** the reported payload names the endpoint as unreachable or not answering
- **AND** the payload still carries the underlying reset detail for diagnosis

### Requirement: Play-mode commands preserve formal exit codes for non-success answers

When a play-mode command receives a machine-readable non-success status from the control
endpoint (for example `modal_blocked` or `empty_response`), the process SHALL exit with
that status's formal exit code. It SHALL NOT collapse distinct non-success states into one
generic failure code.

#### Scenario: A blocking dialog preserves its exit code

- **WHEN** the play-mode endpoint reports `modal_blocked`
- **THEN** the `play` / `pause` / `stop` process exits with the formal `modal_blocked` exit code
- **AND** the payload carries the `modal_blocked` status and its blocker details

#### Scenario: Distinct non-success states stay distinguishable

- **WHEN** two different non-success statuses are returned by the play-mode endpoint across invocations
- **THEN** each maps to its own formal exit code
- **AND** the two invocations are distinguishable by exit code alone

### Requirement: Play-mode commands follow the project's published endpoint

In project mode, `play`, `pause`, and `stop` SHALL locate the Editor endpoint on every state probe by first confirming the Editor's endpoint publication. They SHALL fall back to an ownership-checked port scan only when the publication cannot be confirmed. This SHALL keep the probe on the project's Editor across the domain reloads that play-mode transitions cause, including when another project's Editor is running on the same machine.

#### Scenario: Stop observes edit mode after the exit's domain reload

- **WHEN** an agent runs `stop --project-path Project` with a relative path and the Editor leaves play mode
- **AND** the exit's domain reload republishes the endpoint with a new session marker
- **THEN** the command observes `play_state: "edit"` from the republished endpoint
- **AND** it returns `status: "completed"` rather than `running`

#### Scenario: Another project's Editor is not probed as the target

- **WHEN** a second project's Editor is ready on the preferred control port
- **AND** an agent runs a play-mode command for the first project
- **THEN** every state probe reads the first project's Editor
- **AND** the second Editor's play state never satisfies the command

### Requirement: An unresolved endpoint is reported distinctly from an unfinished transition

When a play-mode command's budget elapses without any probe reaching the project's own endpoint, the `running` result SHALL say that the endpoint was not resolved. It SHALL NOT report `play_state: null` in a way that reads as the transition still being in progress. When the endpoint was reached, the result SHALL name the target state and the last observed play state.

#### Scenario: Endpoint never resolved within the budget

- **WHEN** no probe during a `stop` reaches an endpoint owned by the target project before the timeout
- **THEN** the command returns `status: "running"` with a result that marks the endpoint as unresolved
- **AND** its guidance names endpoint resolution as the waiting condition rather than the play-mode exit

#### Scenario: Endpoint reached but transition unfinished

- **WHEN** probes reach the project's endpoint but the Editor has not reached the target state before the timeout
- **THEN** the `running` result names the target play state and the last observed play state

