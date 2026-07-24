## ADDED Requirements

### Requirement: Real-host validation observes a log no unrelated Editor can share

Real-host validation SHALL observe the validation host through a log source private to the host project, so a Unity Editor open on an unrelated project cannot share, rotate, or truncate the file the suite reads. A development machine running several Unity projects at once SHALL remain a supported environment for real-host validation.

#### Scenario: Concurrent unrelated Editor does not invalidate observation

- **WHEN** real-host validation runs while an unrelated Unity Editor is open on a different project
- **THEN** the suite observes the validation host through a host-private log
- **AND** log-based assertions reflect output the validation host actually produced

#### Scenario: Host-private log is established without per-command flags

- **WHEN** the suite brings up the validation host
- **THEN** the host-private log is established at launch
- **AND** individual cases do not each have to supply a log-path flag to observe it

### Requirement: Real-host run instructions state the concurrent-Editor condition

The repository's real-host run instructions SHALL state that a Unity Editor open on an unrelated project shares the platform default per-user Editor log, that this invalidates byte-offset log observation, and that host-private logging is what makes the suite safe to run in that condition. A contributor SHALL be able to recognize the symptom from the instructions rather than by bisecting the product.

#### Scenario: Contributor reads the real-host prerequisites

- **WHEN** a contributor consults the real-host run instructions
- **THEN** the instructions describe the shared-default-log condition and its effect on log observation
- **AND** the instructions state how the host's log is isolated from it

#### Scenario: Contributor diagnoses an observation timeout

- **WHEN** a real-host log-observation case fails with a wait timeout
- **THEN** the instructions let the contributor distinguish an invalidated log source from a product regression
