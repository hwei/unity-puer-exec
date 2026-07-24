## MODIFIED Requirements

### Requirement: Real-host validation covers control-port binding behavior

The repository SHALL maintain repeatable real-host validation expectations that prove the Unity control-port binding contract, covering the uniform activation rule in batch mode (both with and without activation requested) and occupied-preferred-port rollover. These expectations SHALL run only under the existing opt-in real-host gate and SHALL skip cleanly when Unity, the host project, or the required process state is unavailable, so the default mocked/unit workflow is unaffected.

#### Scenario: Contributor validates that a batch-mode process without activation does not start the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched without activation requested
- **THEN** the validation asserts the batch-mode process log records that the control service was not activated for that process
- **AND** the validation asserts the batch-mode process log records no successful control-port bind and no whole-range bind failure

#### Scenario: Contributor validates that a batch-mode process with activation starts the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched with activation requested
- **THEN** the validation asserts the batch-mode process log records a successful control-port bind
- **AND** the validation asserts the batch-mode process log does not record that the control service was not activated

#### Scenario: Contributor validates rollover when the preferred control port is occupied

- **WHEN** a contributor runs the real-host validation with the preferred control port already occupied at the time an interactive control service starts
- **THEN** the validation asserts the interactive control service becomes ready on a later port in the bounded range rather than failing the whole scan
- **AND** the validation asserts the ready health identity reports the later selected port and its base URL

#### Scenario: Prerequisites for binding validation are absent

- **WHEN** the real-host gate is disabled, or Unity / the host project / the required process state is unavailable
- **THEN** the binding-behavior validation skips with a machine-usable reason
- **AND** it does not report a failure that would be indistinguishable from a real binding regression

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
