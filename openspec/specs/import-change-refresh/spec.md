# import-change-refresh Specification

## Purpose
Make project refresh automatic for code changes only, so a caller never has to remember that a C# edit needs a refresh before the next exec, without paying the cost of refreshing on every exec.

## Requirements

### Requirement: Refresh triggers only when a compile-triggering change is detected

The Unity control service SHALL observe changes to compile-triggering project files and SHALL perform an `AssetDatabase.Refresh()` before executing a script when, and only when, it detects a change that requires recompilation. Compile-triggering files SHALL comprise C# script sources, assembly definition and reference files, and compiler response files. Changes to scenes, prefabs, metadata files, textures, audio, and all other non-code assets SHALL NOT trigger a refresh. A file whose path contains a directory segment whose name starts with `.`, within the watched `Assets/` or `Packages/` tree, SHALL NOT count as a detected change.

#### Scenario: C# source changes before exec

- **WHEN** a `.cs` file under the project's `Assets/` or `Packages/` tree is written after the last settled import
- **AND** no directory segment in that path starts with `.`
- **AND** a new exec request arrives
- **THEN** the server refreshes the project before executing the script
- **AND** the refresh completes before script execution begins

#### Scenario: Assembly definition changes before exec

- **WHEN** an `.asmdef` or `.asmref` file is written after the last settled import
- **AND** no directory segment in that path starts with `.`
- **AND** a new exec request arrives
- **THEN** the server refreshes the project before executing the script

#### Scenario: Non-code asset change does not trigger refresh

- **WHEN** a `.unity` scene, `.prefab`, `.meta`, texture, or audio file is written after the last settled import
- **AND** no compile-triggering file changed
- **AND** a new exec request arrives
- **THEN** the server does not refresh
- **AND** the exec proceeds without a refresh step

#### Scenario: No change at all proceeds immediately

- **WHEN** no compile-triggering file changed since the last settled import
- **AND** a new exec request arrives
- **THEN** the server does not refresh and does not walk the project tree
- **AND** the exec proceeds to its normal job creation and execution path

#### Scenario: A compile-triggering file inside a dot-directory does not refresh

- **WHEN** a `.cs`, `.asmdef`, `.asmref`, or `.rsp` file is written under a directory whose name starts with `.`
- **AND** no other compile-triggering file changed
- **AND** a new exec request arrives
- **THEN** the change signal is not pending
- **AND** the server does not refresh
- **AND** the exec proceeds without waiting for a compilation

#### Scenario: A dot segment above the watched root does not suppress detection

- **WHEN** a compile-triggering file is written under the watched `Assets/` or `Packages/` tree
- **AND** an ancestor of that root on disk has a directory whose name starts with `.`
- **AND** no directory segment below the watched root starts with `.`
- **AND** a new exec request arrives
- **THEN** the change is detected
- **AND** the server refreshes the project before executing the script

### Requirement: Settled-import timestamp advances only on Unity completion signals

The control service SHALL maintain a project-wide timestamp recording when the most recent import and compilation cycle settled. The service SHALL advance that timestamp only when Unity signals that a compilation or assembly reload has completed. The service SHALL NOT advance it as a consequence of performing a refresh or executing a script. The timestamp SHALL survive domain reload.

#### Scenario: Compilation completion advances the timestamp

- **WHEN** Unity reports that a compilation cycle finished
- **THEN** the service advances the settled-import timestamp to that moment

#### Scenario: Assembly reload advances the timestamp

- **WHEN** Unity completes an assembly reload
- **THEN** the service advances the settled-import timestamp

#### Scenario: Timestamp survives domain reload

- **WHEN** a domain reload completes
- **AND** an exec request arrives before any further file change
- **THEN** the service still knows the timestamp from before the reload
- **AND** it does not treat the reload itself as a pending change

#### Scenario: Refreshing does not advance the timestamp

- **WHEN** the service performs an automatic refresh
- **AND** that refresh triggers no compilation or reload completion signal
- **THEN** the settled-import timestamp is not advanced by the refresh itself

### Requirement: Repeated execs after a single change do not refresh repeatedly

Because importing a file does not alter its modification time, the settled-import timestamp is the only thing distinguishing an already-imported change from a new one. After a change has been imported and its compilation has settled, subsequent exec requests SHALL NOT trigger another refresh for that same change.

#### Scenario: Second exec after a settled import does not refresh again

- **WHEN** a `.cs` change triggered a refresh whose compilation then settled
- **AND** no further file changed
- **AND** another exec request arrives
- **THEN** the server does not refresh again
- **AND** the exec proceeds directly to execution

#### Scenario: A genuinely new change does refresh again

- **WHEN** a compile-triggering file is written again after the previous compilation settled
- **AND** a new exec request arrives
- **THEN** the server refreshes again

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

### Requirement: Exec responses disclose the refresh decision

When a refresh decision is made, the exec response SHALL disclose whether a refresh was triggered, why, and which paths were involved. When no refresh occurred, the response SHALL disclose why it was skipped. The response SHALL include the settle outcome and the elapsed time of the refresh step.

#### Scenario: Response reports a triggered refresh

- **WHEN** the server refreshed before executing a script
- **THEN** the response reports the refresh as triggered
- **AND** the response names the reason and the changed paths that caused it
- **AND** the response reports the settle outcome and elapsed time

#### Scenario: Response reports a skipped refresh

- **WHEN** the server did not refresh
- **THEN** the response reports the refresh as not triggered
- **AND** the response names the reason it was skipped

#### Scenario: Response reports a play-mode skip

- **WHEN** the server skipped the refresh because the Editor is in play mode
- **THEN** the response names play mode as the skip reason

### Requirement: Refresh decision diagnostics remain available for precision measurement

The false-positive rate of the change signal is not knowable without measurement on a real project. The refresh diagnostics SHALL be present in the response rather than deferred, so that observed precision and elapsed cost can be evaluated from ordinary transcripts.

#### Scenario: Diagnostics are observable without special instrumentation

- **WHEN** an operator wants to know why a refresh happened on a given exec
- **THEN** the ordinary exec response contains enough of the decision to answer that
- **AND** no separate diagnostic command or build is required

### Requirement: Wait-for-exec discloses a play-mode compile block like exec

When a `wait-for-exec` response covers a request that ran while the Editor was in play mode
with a compile-triggering change pending, the response SHALL carry the same
`compile_blocked` disclosure and warning status as the equivalent `exec` response. A
terminal response SHALL NOT report a plain success in that case. The same precedence rules
apply: a failure status or an existing async warning keeps its status and code, and the
`compile_blocked` object is attached in every case.

#### Scenario: Continued request reports the play-mode block

- **WHEN** an `exec` request is continued with `wait-for-exec`
- **AND** the Editor is in play mode
- **AND** a compile-triggering change was pending when the script ran
- **THEN** the terminal `wait-for-exec` response reports `status: "warning"` with `warning: "compile_blocked_by_play_mode"`
- **AND** it carries a `compile_blocked` object naming `play_mode` as the reason
- **AND** it lists the pending paths when the service knows them

#### Scenario: Recovered failure keeps its status and still carries the object

- **WHEN** the continued request fails
- **AND** a compile-triggering change was pending while the Editor was in play mode
- **THEN** the response keeps the failure status it would report outside play mode
- **AND** it still carries the `compile_blocked` object

#### Scenario: Nothing pending is unchanged

- **WHEN** no compile-triggering change is pending
- **AND** the Editor is in play mode
- **THEN** the `wait-for-exec` response reports the status it reports today
- **AND** it carries no `compile_blocked` object

#### Scenario: Non-terminal response is not rewritten

- **WHEN** `wait-for-exec` returns a non-terminal `running` / `refreshing` response
- **THEN** the response is not annotated with a `compile_blocked` object

### Requirement: Change detection is the incremental filesystem scan alone

The control service SHALL detect compile-triggering changes by walking the watched roots
on each decision, with no dependency on a live filesystem watcher. A change SHALL be
detected when a compile-triggering file's modification time is newer than the
settled-import timestamp, including changes made before the service installed and changes
made across a domain reload. The decision SHALL NOT depend on in-memory event state that a
domain reload discards.

#### Scenario: A change made before the service was installed is detected

- **WHEN** a compile-triggering file is changed while no service state exists
- **AND** the service becomes ready and an exec request arrives
- **THEN** the scan detects the change and the server refreshes

#### Scenario: A change across a domain reload is detected

- **WHEN** a compile-triggering file is changed across a domain reload
- **AND** an exec request arrives
- **THEN** the scan detects the change and the server refreshes
- **AND** the detection does not depend on any watcher having been attached before or
  after the reload

#### Scenario: Detection holds with no watcher present

- **WHEN** no filesystem watcher is attached in the Editor process
- **THEN** a compile-triggering change is still detected on the next decision

#### Scenario: Non-code and no-change decisions are unaffected

- **WHEN** the scan finds only non-code changes, or no change
- **THEN** the server does not refresh
- **AND** the extension filter and the settled-import comparison are unchanged
