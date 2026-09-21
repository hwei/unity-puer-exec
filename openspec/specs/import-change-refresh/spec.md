# import-change-refresh Specification

## Purpose
Make project refresh automatic for code changes only, so a caller never has to remember that a C# edit needs a refresh before the next exec, without paying the cost of refreshing on every exec.

## Requirements

### Requirement: Refresh triggers only when a compile-triggering change is detected

The Unity control service SHALL observe changes to compile-triggering project files and SHALL perform an `AssetDatabase.Refresh()` before executing a script when, and only when, it detects a change that requires recompilation. Compile-triggering files SHALL comprise C# script sources, assembly definition and reference files, and compiler response files. Changes to scenes, prefabs, metadata files, textures, audio, and all other non-code assets SHALL NOT trigger a refresh.

#### Scenario: C# source changes before exec

- **WHEN** a `.cs` file under the project's `Assets/` or `Packages/` tree is written after the last settled import
- **AND** a new exec request arrives
- **THEN** the server refreshes the project before executing the script
- **AND** the refresh completes before script execution begins

#### Scenario: Assembly definition changes before exec

- **WHEN** an `.asmdef` or `.asmref` file is written after the last settled import
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

### Requirement: Refresh decision survives watcher failure modes

The change signal SHALL NOT depend solely on a live filesystem watcher having observed every event. When the watcher reports an error, when its internal buffer overflows, or when the service installs its watcher, the service SHALL treat the project as possibly changed rather than silently reporting no change.

#### Scenario: Watcher reports an error

- **WHEN** the filesystem watcher raises an error event, including internal buffer overflow
- **AND** a new exec request arrives
- **THEN** the server treats the project as changed and refreshes

#### Scenario: Changes made before the service installed its watcher

- **WHEN** a compile-triggering file was changed before the control service installed its watcher
- **AND** a new exec request arrives
- **THEN** the server detects that pending change at watcher-install time and refreshes

#### Scenario: Domain reload resets watcher state

- **WHEN** a domain reload resets the watcher's in-memory state
- **AND** a compile-triggering file changed across that reload
- **AND** a new exec request arrives
- **THEN** the server detects the change and refreshes

### Requirement: An invalidated signal forces one refresh, then re-establishes trust

When the service cannot trust its change signal — a watcher error event, or any
state where events may have been dropped — the next refresh decision SHALL treat the
project as changed and refresh it once rather than reporting no change. Because the
decision's own scan is the authoritative signal, the service SHALL re-establish trust
from that same decision: once a decision has consumed the invalidation, the service
SHALL NOT keep forcing a refresh on subsequent requests that observe no change. Until
a decision consumes it, the health endpoint SHALL keep reporting the pending state as
unknown rather than as a false negative.

This bounds the fallback so an invalidation cannot become an unconditional per-exec
refresh — a liveliness failure the design treats as more severe than a one-shot miss.

#### Scenario: An invalidated signal refreshes exactly once

- **WHEN** the change signal is invalidated
- **AND** an exec request arrives
- **THEN** the server refreshes before executing the script
- **AND** the response names the unavailable signal as the refresh reason
- **AND** the script still executes

#### Scenario: Trust is re-established after the invalidation is consumed

- **WHEN** a refresh decision has consumed an invalidation
- **AND** another exec request arrives with no further file change
- **THEN** the server does not refresh again

#### Scenario: Health reports unknown until a decision consumes the invalidation

- **WHEN** the change signal is invalidated
- **AND** a caller probes `/health` before any exec request arrives
- **THEN** the response reports the pending state as unknown

#### Scenario: Health resolves once the invalidation is consumed

- **WHEN** a refresh decision has consumed an invalidation
- **AND** a caller probes `/health`
- **THEN** the response reports the pending state normally rather than unknown

### Requirement: Play mode skips the refresh without discarding the change signal

Unity defers compilation while the Editor is in play mode, so refreshing there would wait for a compilation that cannot start. When the Editor is in play mode, the service SHALL skip the automatic refresh and SHALL report the skip reason. The service SHALL NOT clear the pending change signal as a result of skipping.

#### Scenario: Exec during play mode skips refresh visibly

- **WHEN** a compile-triggering change is pending
- **AND** the Editor is in play mode
- **AND** a new exec request arrives
- **THEN** the server does not refresh
- **AND** the response reports a skip reason identifying play mode
- **AND** the script still executes

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
