# Spec Delta

## ADDED Requirements

### Requirement: Content already handed to a dispatched refresh is not a pending change

A modification time newer than the settled-import timestamp SHALL make a compile-triggering
file a refresh candidate, not a verdict. The service SHALL remember, per path, the content it
handed to a refresh it successfully dispatched since the settled-import timestamp last
advanced, and SHALL drop a candidate whose current content matches that record. The record
SHALL be dropped whenever the settled-import timestamp advances.

#### Scenario: A content-identical rewrite stops the refresh loop

- **WHEN** a compile-triggering file is rewritten with unchanged content, so its modification
  time is newer than the settled-import timestamp
- **AND** a refresh was dispatched for that content and Unity started no compilation
- **AND** further exec requests arrive with no further change to that file
- **THEN** the service stops reporting the file as a triggering change
- **AND** the exec proceeds to its normal job creation and execution path

#### Scenario: A play transition completes after a content-identical rewrite

- **WHEN** a compile-triggering file was rewritten with unchanged content
- **AND** a `play` request arrives
- **THEN** the pre-play settle reaches the play-mode transition within its own budget
- **AND** it does not report the refreshing phase until that budget elapses

#### Scenario: A genuine content change after a suppressed decision refreshes again

- **WHEN** a candidate was dropped because its content matched the recorded content
- **AND** that file is then written with different content
- **AND** a new exec request arrives
- **THEN** the service refreshes for the new content

#### Scenario: The record does not outlive the settled-import timestamp

- **WHEN** the settled-import timestamp advances on a Unity completion signal
- **AND** a compile-triggering file is written after that moment
- **AND** a new exec request arrives
- **THEN** the service refreshes, whatever content the file carried before the advance

#### Scenario: A failed dispatch records nothing

- **WHEN** a refresh dispatch fails
- **THEN** the content of the paths that triggered it is not recorded
- **AND** a later decision for the same content still triggers a refresh

#### Scenario: Content that cannot be read is never suppressed

- **WHEN** a candidate's content cannot be read at decision time
- **THEN** the candidate is not dropped
- **AND** the decision treats it as a compile-triggering change

### Requirement: Suppression waits for Unity's chance to compile

The service SHALL drop a candidate on a matching content record only once Unity has had its
chance to compile that content: the record SHALL be at least a bounded age past its dispatch,
that age SHALL stay inside a caller's compile-appear budget, and the Editor SHALL be neither
compiling nor importing at the decision. Dispatching the same content again SHALL NOT restart
the age.

#### Scenario: Suppression waits for Unity's chance to compile

- **WHEN** a refresh was dispatched for a candidate's content
- **AND** a further decision arrives before that dispatch is a bounded age old
- **THEN** the candidate is not dropped
- **AND** the decision still treats it as a compile-triggering change

#### Scenario: The bounded age stays inside the caller's compile-appear budget

- **WHEN** a caller waits out its own compile-appear budget after a dispatched refresh and
  then re-asks once
- **THEN** the service has already stopped treating the unchanged content as triggering
- **AND** the caller reaches a terminal outcome on that re-ask instead of looping

#### Scenario: A candidate is not suppressed while the Editor is compiling or importing

- **WHEN** a candidate's content matches a record old enough to suppress
- **AND** the Editor is compiling or importing at the decision
- **THEN** the candidate is not dropped

#### Scenario: A failing build is reported instead of suppressed

- **WHEN** a compile-triggering file was written with content that does not compile
- **AND** a refresh was dispatched for it
- **AND** a further decision arrives before that compilation finished
- **THEN** the candidate is not dropped
- **AND** the service reports the failed compilation rather than a settled build

#### Scenario: A re-dispatch does not extend the bounded age

- **WHEN** a caller re-asks before the bounded age elapsed and the service dispatches the
  same content again
- **THEN** the record keeps the age of the first dispatch for that content
- **AND** the bounded age still elapses

### Requirement: The pending-change view and the refresh decision agree

The pending-change state the service reports for health and blocker purposes SHALL apply the
same content filter as the refresh decision, so a caller cannot observe a pending change that
the next exec or refresh request would not act on.

#### Scenario: Health reports not pending for suppressed content

- **WHEN** every scanned candidate is dropped because its content was already handed to a
  dispatched refresh
- **AND** a health request arrives
- **THEN** the pending state is reported as not pending

#### Scenario: Health still reports a pending change the decision would act on

- **WHEN** at least one candidate carries content the service has not dispatched a refresh for
- **AND** a health request arrives
- **THEN** the pending state is reported as pending

## MODIFIED Requirements

### Requirement: Change detection is the incremental filesystem scan alone

The control service SHALL detect compile-triggering changes by walking the watched roots
on each decision, with no dependency on a live filesystem watcher. A change SHALL be
detected when a compile-triggering file's modification time is newer than the
settled-import timestamp, including changes made before the service installed and changes
made across a domain reload. The scan yields refresh candidates; the service then drops a
candidate whose content it already handed to a successfully dispatched refresh. The
decision SHALL NOT depend on in-memory event state that a domain reload discards: losing
the content record across a reload restores the unfiltered candidate, so a reload can only
make detection more eager, never less.

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

#### Scenario: Unflagged trees cost no content read

- **WHEN** a decision scans the watched roots and no compile-triggering file is newer than
  the settled-import timestamp
- **THEN** the decision reads no file content
- **AND** it costs directory enumeration and modification-time reads only

### Requirement: Exec responses disclose the refresh decision

When a refresh decision is made, the exec response SHALL disclose whether a refresh was triggered, why, and which paths were involved. When no refresh occurred, the response SHALL disclose why it was skipped. The response SHALL include the settle outcome and the elapsed time of the refresh step. The response SHALL also name the paths the scan flagged as candidates and the service then suppressed as content it had already dispatched a refresh for, so a suppressed decision is distinguishable from a decision that saw no candidate at all.

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

#### Scenario: Response reports suppressed candidates

- **WHEN** the scan flagged candidates that the service dropped because their content had
  already been handed to a dispatched refresh
- **THEN** the response reports the refresh as not triggered
- **AND** the response names those paths as suppressed

#### Scenario: A decision with no candidate reports no suppressed path

- **WHEN** the scan flagged no compile-triggering candidate
- **THEN** the response reports an empty suppressed-path list

### Requirement: Repeated execs after a single change do not refresh repeatedly

Because importing a file does not alter its modification time, the settled-import timestamp is what distinguishes an already-imported change from a new one, and the recorded content of a dispatched refresh is what distinguishes an already-refreshed change from one Unity resolved without compiling. After a change has been imported and its compilation has settled, or after a refresh for that change's content has been dispatched and Unity started no compilation, subsequent exec requests SHALL NOT trigger another refresh for that same change.

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

#### Scenario: A rewrite that Unity resolves without compiling does not refresh forever

- **WHEN** a compile-triggering file's modification time moves past the settled-import
  timestamp without its content changing
- **AND** the refresh dispatched for it starts no compilation, so no completion signal
  advances the timestamp
- **AND** further exec requests arrive with no further change
- **THEN** the server stops reporting that content as a triggering change once Unity has had
  its chance to compile it
- **AND** later decisions report the change as suppressed rather than triggering
- **AND** a caller that re-asks after its own compile-appear budget reaches a terminal
  outcome instead of exhausting its refresh budget
