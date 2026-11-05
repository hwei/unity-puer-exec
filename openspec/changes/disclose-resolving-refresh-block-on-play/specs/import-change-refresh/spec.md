# Spec Delta

## MODIFIED Requirements

### Requirement: Exec responses disclose the refresh decision

When a refresh decision is made, the exec response SHALL disclose whether a refresh was triggered, why, and which paths were involved. When no refresh occurred, the response SHALL disclose why it was skipped. The response SHALL include the settle outcome and the elapsed time of the refresh step. The response SHALL also name the paths the scan flagged as candidates and the service then suppressed as content it had already dispatched a refresh for, so a suppressed decision is distinguishable from a decision that saw no candidate at all. When one exec invocation dispatched a refresh on an earlier poll and resolved on a later decision, the terminal response SHALL disclose both: the dispatch as it is reported today, and the resolving decision including the paths it suppressed.

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

#### Scenario: A dispatch followed by a suppressing resolution discloses both decisions

- **WHEN** an exec invocation dispatched a refresh on an earlier poll
- **AND** the poll that resolved the request suppressed one or more paths
- **THEN** the response still reports the refresh as triggered, with every field it reports today
- **AND** the response names the resolving decision's suppressed paths
- **AND** the resolving decision is available verbatim alongside the dispatch
