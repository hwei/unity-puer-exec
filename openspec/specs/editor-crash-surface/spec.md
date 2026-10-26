# editor-crash-surface Specification

## Purpose
Detects that the Unity Editor process died while an accepted exec script was running, guarantees that such a request is never executed a second time, and reports the crash to the caller as its own terminal outcome with evidence instead of a transport failure.

## Requirements

### Requirement: The service journals a request before executing its script

Before the Unity-side service hands an accepted exec script to the script engine, it SHALL persist a start journal entry for that `request_id` under the project's `Temp/UnityPuerExec/` directory. The entry SHALL identify the Editor process (process id and process start time) and the UTC start time, and SHALL be on disk before script execution begins.

#### Scenario: Journal entry exists while the script runs

- **WHEN** the service accepts a new exec request `R` and starts executing its script
- **THEN** a start journal entry for `R` exists on disk naming the current Editor process and the start time
- **AND** the entry was written before the script engine began executing `R`

#### Scenario: Request that never started has no journal entry

- **WHEN** an exec request is rejected or deferred before execution, for example as `busy`, `compiling`, `refreshing`, `unity_compile_error`, or `module_cache_stale`
- **THEN** no start journal entry is written for that request

### Requirement: The service removes the journal entry at a terminal outcome

The service SHALL remove a request's start journal entry when that request reaches any terminal outcome inside the same Editor process, including `completed`, `failed`, and `warning`.

#### Scenario: Completed request leaves no journal entry

- **WHEN** exec request `R` completes, fails, or completes with a warning
- **THEN** the start journal entry for `R` no longer exists

### Requirement: A request started by a dead Editor process is never re-executed

When a service instance receives `exec` for a `request_id` that has no in-memory record but has a start journal entry naming a different Editor process, the service SHALL NOT execute the script. It SHALL answer with the terminal status `editor_crashed_during_request`. This SHALL hold for both the `--project-path` and `--base-url` selectors.

#### Scenario: Replay after an Editor crash is refused

- **WHEN** the Editor process that started exec request `R` died before `R` reached a terminal outcome
- **AND** a new Editor process receives `exec` for `R` with equivalent content
- **THEN** the new Editor does not execute the script
- **AND** the response status is `editor_crashed_during_request`

#### Scenario: Wait after an Editor crash reports the crash instead of missing

- **WHEN** a new Editor process receives `wait-for-exec` for a `request_id` whose start journal entry names a different, dead Editor process
- **THEN** the response status is `editor_crashed_during_request` rather than `missing`

### Requirement: Project-scoped commands report a crash without relaunching or replaying

Project-scoped `exec` and `wait-for-exec` SHALL check the start journal for the request before they relaunch Unity or replay a pending artifact. When the journal entry exists and its Editor process is no longer running, the CLI SHALL return `editor_crashed_during_request`, SHALL NOT launch Unity, and SHALL NOT resubmit the script. The crashed Editor's log SHALL therefore remain as the crash left it.

#### Scenario: Wait-for-exec after a crash does not relaunch Unity

- **WHEN** project-scoped `exec` for `R` ended in `not_available` because the Editor crashed while running `R`
- **AND** the caller invokes `wait-for-exec --project-path P --request-id R` after the Editor process has exited
- **THEN** the command returns `editor_crashed_during_request`
- **AND** no Unity process is launched by that command
- **AND** the script for `R` is not submitted again

#### Scenario: Exec notices the crash on its own submit

- **WHEN** project-scoped `exec` for `R` loses its connection while `R` is running
- **AND** the Editor process named by the journal entry exits within the CLI's short crash grace window
- **THEN** that same `exec` invocation returns `editor_crashed_during_request` instead of `not_available`

#### Scenario: Crash report is stable across repeated waits

- **WHEN** the caller invokes `wait-for-exec --request-id R` more than once after the crash
- **THEN** each invocation returns `editor_crashed_during_request` while the journal entry is within its retention window

#### Scenario: Request that never started keeps the existing replay path

- **WHEN** a pending artifact exists for `R` and no start journal entry exists for `R`
- **THEN** project-scoped `wait-for-exec` keeps the existing behavior of preparing Unity and replaying the pending request

### Requirement: The crash response is terminal and carries evidence

The `editor_crashed_during_request` response SHALL be terminal, SHALL use exit code 26, and SHALL carry `request_id`, the crashed Editor's process id, the request start time, `resubmit_safe: false`, a `situation` stating that the Editor died while the script was running and that the request was not re-run, and `next_steps`. It SHALL carry the Editor log path and the Unity crash report directory when the CLI can locate them.

#### Scenario: Crash response names the evidence

- **WHEN** the CLI returns `editor_crashed_during_request` for `R`
- **THEN** the payload contains `ok: false`, `request_id`, `editor_pid`, `started_at`, and `resubmit_safe: false`
- **AND** the payload contains `editor_log_path` when the log path is known and `crash_report_dir` when a Unity crash report created after `started_at` is found
- **AND** the process exit code is 26

#### Scenario: Next steps do not offer a blind replay

- **WHEN** the CLI returns `editor_crashed_during_request`
- **THEN** `next_steps` does not offer `wait-for-exec` for the same `request_id` or `exec` with the same `request_id`
- **AND** the `situation` tells the caller to fix the script and submit it as a new request, and that the next project-scoped command relaunches the Editor

### Requirement: Start journal entries are bounded local state

Start journal entries for crashed requests SHALL be retained for a bounded window and then removed opportunistically by the CLI or the service. Malformed entries SHALL be removed and SHALL NOT be treated as evidence of a crash.

#### Scenario: Expired or malformed journal entries are swept

- **WHEN** project-scoped `exec` or `wait-for-exec`, or a starting service, finds a journal entry older than the retention window or one that cannot be parsed
- **THEN** that entry is removed
- **AND** it does not produce `editor_crashed_during_request`

### Requirement: Help lists the crash status

The help surface for `exec` and `wait-for-exec` SHALL list `editor_crashed_during_request` with exit code 26 among the failure statuses, and SHALL state that the request was not re-run.

#### Scenario: Caller discovers the crash status from help

- **WHEN** a caller reads `unity-puer-exec exec --help` or `unity-puer-exec wait-for-exec --help`
- **THEN** the failure status table includes `editor_crashed_during_request` with exit code 26
