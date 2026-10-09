## MODIFIED Requirements

### Requirement: Play mode skips the refresh without discarding the change signal

Unity defers compilation while the Editor is in play mode, so refreshing there would wait for a compilation that cannot start. When the Editor is in play mode, the service SHALL skip the automatic refresh and SHALL report the skip reason. The service SHALL NOT clear the pending change signal as a result of skipping. When the skip leaves a compile-triggering change pending, the exec response SHALL NOT report a plain success: it SHALL report a warning that the script ran against code that does not include the pending change.

#### Scenario: Exec during play mode skips refresh visibly

- **WHEN** a compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** a new exec request arrives
- **THEN** the server does not refresh
- **AND** the response reports a skip reason identifying play mode
- **AND** the script still executes

#### Scenario: Exec during play mode with a pending change reports a warning

- **WHEN** a compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** an exec script completes without error
- **THEN** the response has `ok: true` and `status: "warning"` with `warning: "compile_blocked_by_play_mode"`
- **AND** the response carries a `compile_blocked` object naming `play_mode` as the reason
- **AND** the `compile_blocked` object lists the pending paths when the service knows them
- **AND** the script's return value is still reported in `result`

#### Scenario: Exec during play mode with nothing pending is unchanged

- **WHEN** no compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** an exec script completes without error
- **THEN** the response reports `status: "completed"` as before
- **AND** the response carries no `compile_blocked` object

#### Scenario: A script failure takes precedence over the play-mode warning

- **WHEN** a compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** the exec script throws
- **THEN** the response reports the failure status it would report outside play mode
- **AND** the response still carries the `compile_blocked` object

#### Scenario: An async-result warning keeps its code alongside the play-mode block

- **WHEN** a compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** the exec entry function returns a Promise
- **THEN** the response reports `status: "warning"` with `warning: "async_result_not_supported"`
- **AND** the response still carries the `compile_blocked` object

#### Scenario: Pending change survives a play-mode skip

- **WHEN** a refresh was skipped because the Editor was in play mode
- **AND** the Editor later exits play mode
- **AND** a new exec request arrives with no further file change
- **THEN** the server refreshes for the still-pending change
