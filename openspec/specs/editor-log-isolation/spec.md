# editor-log-isolation Specification

## Purpose
TBD - created by archiving change isolate-validation-host-editor-log. Update Purpose after archive.
## Requirements
### Requirement: The running Editor states its own log path

The Unity bridge SHALL report the log path of the Editor process it runs inside, resolved from that process's own Unity runtime rather than from a platform convention, so a caller never has to infer where the Editor writes.

#### Scenario: Bridge reports the log path of a default-launched Editor

- **WHEN** a caller probes a ready service in an Editor started without a log-path override
- **THEN** the reported log path is the path that Editor process is actually writing to

#### Scenario: Bridge reports the log path of an override-launched Editor

- **WHEN** a caller probes a ready service in an Editor started with an explicit log-path override
- **THEN** the reported log path is the override path, not the platform default path

#### Scenario: Log path is unavailable

- **WHEN** the bridge cannot resolve its Editor's log path
- **THEN** the reported value SHALL be omitted or null rather than a guessed platform default
- **AND** the rest of the health response remains well-formed

### Requirement: The CLI prefers a stated log path over a platform guess

When resolving the effective Unity log source, the CLI SHALL prefer a log path stated by the bridge over the platform default path. Explicit caller intent and an established session artifact SHALL continue to take precedence over the stated path, so the new tier corrects only the case that was previously a guess.

#### Scenario: Bridge-stated path replaces the platform default

- **WHEN** no explicit log path is supplied and no session artifact log path exists
- **AND** a reachable bridge states its log path
- **THEN** the CLI observes that path
- **AND** the CLI does not fall back to the platform default path

#### Scenario: Explicit caller intent still wins

- **WHEN** a caller supplies an explicit log path and the bridge states a different one
- **THEN** the CLI observes the caller-supplied path

#### Scenario: Established session artifact still wins

- **WHEN** a session artifact records an effective log path and the bridge states a different one
- **THEN** the CLI observes the session artifact path
- **AND** log observation continues to work when the control service is unreachable

#### Scenario: No stated path is available

- **WHEN** no explicit path, no session artifact path, and no bridge-stated path can be obtained
- **THEN** the CLI falls back to the platform default path as a last resort

### Requirement: Launch-driven sessions receive a project-private log

When the CLI launches Unity for a project-scoped workflow without an explicit log-path override, it SHALL direct that Editor to a log location private to the target project, so a concurrently running unrelated Editor cannot share, rotate, or truncate the log the session is observed through.

#### Scenario: CLI-launched Editor does not share the per-user log

- **WHEN** the CLI launches Unity for a project and no explicit log path was supplied
- **THEN** the Editor writes to a project-private log location
- **AND** that location is distinct from the platform default per-user Editor log

#### Scenario: Explicit override still controls the launch

- **WHEN** a caller supplies an explicit log path on a launch-driven command
- **THEN** the Editor is launched with that path instead of the project-private default

#### Scenario: Observation follows the launched Editor without extra flags

- **WHEN** a project-private log was established at launch
- **THEN** later log-related commands for that project observe the same log without the caller repeating a log-path flag

### Requirement: Invalidated log offsets are reported

When a caller supplies a log start offset that lies beyond the current end of the observed log, the CLI SHALL report that the offsets were invalidated rather than silently restarting the scan, because a byte range from before a rotation or truncation no longer denotes the content the caller intended.

#### Scenario: Offset beyond end of file is surfaced

- **WHEN** an observation is given a start offset greater than the current size of the observed log
- **THEN** the response indicates that the supplied offset was invalidated
- **AND** the indication names the observed log path

#### Scenario: A fresh observation cannot trip the signal

- **WHEN** an observation supplies no start offset
- **THEN** no invalidation is reported

#### Scenario: Reading still proceeds

- **WHEN** an offset is reported as invalidated
- **THEN** the command still returns whatever the observed log currently contains rather than refusing to read

