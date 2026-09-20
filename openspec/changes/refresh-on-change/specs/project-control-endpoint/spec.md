## ADDED Requirements

### Requirement: Health response exposes whether a code change is pending refresh

The Unity-side health endpoint SHALL report whether the control service currently considers a compile-triggering change pending, so that a caller observing an Editor can distinguish "no refresh needed" from "refresh will happen on the next exec" without triggering an exec. The field SHALL be present on ready health responses. When the service cannot determine its pending state — for example because its change signal was invalidated by a watcher error or by a domain reload that reset in-memory state — the response SHALL report the pending state as unknown rather than reporting a false negative.

#### Scenario: Caller probes health with no pending change

- **WHEN** a caller probes `/health` on a ready service
- **AND** no compile-triggering change is pending
- **THEN** the health response reports that no refresh is pending

#### Scenario: Caller probes health with a pending change

- **WHEN** a caller probes `/health` on a ready service
- **AND** a compile-triggering change is pending but not yet refreshed
- **THEN** the health response reports that a refresh is pending

#### Scenario: Pending state is unknown after a signal failure

- **WHEN** the change signal is invalidated by a watcher error or a domain reload
- **AND** a caller probes `/health`
- **THEN** the health response reports the pending state as unknown
- **AND** it does not report that no refresh is pending

### Requirement: Health response exposes whether automatic refresh is currently suppressed

The health endpoint SHALL report when automatic refresh is suppressed because the Editor is in play mode, together with the reason. A caller SHALL be able to observe that a pending change will not be refreshed until play mode exits.

#### Scenario: Editor is in play mode with a pending change

- **WHEN** a caller probes `/health` while the Editor is in play mode
- **AND** a compile-triggering change is pending
- **THEN** the health response reports that refresh is suppressed
- **AND** it reports play mode as the reason

#### Scenario: Editor is not in play mode

- **WHEN** a caller probes `/health` while the Editor is not in play mode
- **THEN** the health response does not report refresh as suppressed for that reason
