## MODIFIED Requirements

### Requirement: Real-host validation observes a log no unrelated Editor can share

Real-host validation SHALL observe the validation host through a log source private to the host project, so a Unity Editor open on an unrelated project cannot share, rotate, or truncate the file the suite reads. A development machine running several Unity projects at once SHALL remain a supported environment for real-host validation.

The suite SHALL establish its clean starting boundary from project-local state — the host project's Unity lockfile and published endpoint — so that a boundary check cannot report the host as stopped while an Editor is still serving it. A case SHALL fail rather than proceed if it would observe a host the suite did not bring up.

#### Scenario: Concurrent unrelated Editor does not invalidate observation

- **WHEN** real-host validation runs while an unrelated Unity Editor is open on a different project
- **THEN** the suite observes the validation host through a host-private log
- **AND** log-based assertions reflect output the validation host actually produced

#### Scenario: Host-private log is established without per-command flags

- **WHEN** the suite brings up the validation host
- **THEN** the host-private log is established at launch
- **AND** individual cases do not each have to supply a log-path flag to observe it

#### Scenario: The boundary cannot pass while the host is still serving

- **WHEN** the suite establishes its starting boundary and an Editor is still serving the host project
- **THEN** the boundary does not report the host as stopped
- **AND** no case proceeds against that Editor

#### Scenario: An unrelated Editor does not block the boundary

- **WHEN** the suite establishes its starting boundary while unrelated Unity Editors are running for other projects
- **THEN** those processes do not prevent the boundary from being established
