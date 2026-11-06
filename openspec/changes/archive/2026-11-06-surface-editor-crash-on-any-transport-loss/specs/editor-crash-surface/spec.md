# Spec Delta

## ADDED Requirements

### Requirement: Every transport loss of an in-flight exec runs the crash check

When project-scoped `exec` for a journalled request loses its response for any transport reason (no connection, a connection reset, or an empty or unparseable response body), the CLI SHALL run the same crash grace check it runs for a lost connection before reporting a transport status.

#### Scenario: Crash surfaces as an empty response body

- **WHEN** project-scoped `exec` for `R` receives an empty or unparseable response body while `R` is running
- **AND** the Editor process named by `R`'s start journal entry exits within the crash grace window
- **THEN** that `exec` invocation returns `editor_crashed_during_request` with exit code 26 instead of `empty_response`

#### Scenario: Empty body from a live Editor keeps the transport status

- **WHEN** project-scoped `exec` for `R` receives an empty response body
- **AND** the Editor process named by `R`'s start journal entry is still running when the grace window ends
- **THEN** the command keeps its existing `empty_response` outcome and guidance

### Requirement: Project-scoped control commands report an Editor that exits mid-command

When a project-scoped `play`, `pause`, `stop`, `wait-for-compile`, `get-compile-errors` or `get-compile-warnings` loses the control endpoint, the CLI SHALL first check whether the Editor process named by the project's endpoint publication has exited. If it exits within the crash grace window, the command SHALL return `editor_crashed_during_request` at once, without retrying or launching Unity.

#### Scenario: Editor crashes while entering play mode

- **WHEN** an agent runs project-scoped `play`
- **AND** the Editor process crashes during the transition, so the control endpoint stops answering
- **THEN** `play` returns `editor_crashed_during_request` with exit code 26 within the crash grace window of the drop, not after its full `--timeout-seconds` budget
- **AND** no Unity process is launched by that command

#### Scenario: A domain reload is still retried

- **WHEN** a project-scoped control command loses the endpoint during a domain reload
- **AND** the published Editor process keeps running
- **THEN** the command keeps its existing re-resolve and retry behavior

#### Scenario: Compile query against a crashed Editor

- **WHEN** an agent runs project-scoped `get-compile-errors` and the Editor process exits while the request is in flight
- **THEN** the command returns `editor_crashed_during_request` with exit code 26 instead of a transport status

### Requirement: The command-level crash response carries evidence

The `editor_crashed_during_request` response of a non-exec command SHALL be terminal, SHALL use exit code 26, and SHALL carry `ok: false`, `operation`, the exited Editor's process id as `editor_pid`, the command start time as `started_at`, a `situation` stating that the Editor process exited while the command was waiting on it, and `next_steps`. It SHALL carry `editor_log_path` when the log path is known and `crash_report_dir` when a Unity crash report created after `started_at` is found.

#### Scenario: Play crash response names the evidence

- **WHEN** `play` returns `editor_crashed_during_request`
- **THEN** the payload contains `ok: false`, `operation: play`, `editor_pid` and `started_at`
- **AND** it contains `crash_report_dir` when Unity wrote a crash report after `started_at`
- **AND** the `situation` does not attribute the drop to a domain reload
- **AND** `next_steps` names inspecting the crash report or Editor log, and states that the next project-scoped command relaunches the Editor

#### Scenario: Help lists the crash status for each affected command

- **WHEN** an agent reads `--help-status` for `play`, `pause`, `stop`, `wait-for-compile`, `get-compile-errors` or `get-compile-warnings`
- **THEN** the status table lists `editor_crashed_during_request` with exit code 26
