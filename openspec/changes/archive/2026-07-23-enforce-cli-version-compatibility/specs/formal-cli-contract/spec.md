## ADDED Requirements

### Requirement: Exit code 24 represents version_mismatch

The CLI SHALL reserve exit code `24` for the `version_mismatch` status, so callers can branch on a mixed installation without parsing prose diagnostics and without confusing it with an execution failure or an unreachable target.

#### Scenario: Mismatch exits with the dedicated code

- **WHEN** a command returns `status = "version_mismatch"`
- **THEN** the process exits with code `24`
- **AND** the exit code is distinct from `1` (unexpected failure), `12` (`not_available`), and `21` (`unity_not_ready`)

#### Scenario: Status is documented in per-command help

- **WHEN** a caller runs `<command> --help-status` for a command that contacts the Unity control service
- **THEN** the non-success status list includes `version_mismatch` with its exit code and an explanation naming both product halves

### Requirement: Version mismatch responses identify both halves

A `version_mismatch` response SHALL carry enough structured detail for a caller to reconcile the installation without further queries. It SHALL name which guard fired, the CLI version, the observed counterpart version, and the location the counterpart was observed at.

#### Scenario: Bridge guard response detail

- **WHEN** the bridge guard reports a mismatch
- **THEN** the response includes the guard identity, the CLI version, the observed `bridge_version` (or null when the bridge reported none), and the control endpoint the version was observed at

#### Scenario: Package-layout guard response detail

- **WHEN** the package-layout guard reports a mismatch
- **THEN** the response includes the guard identity, the CLI version, the version declared by the adjacent `package.json`, and the path of that package

### Requirement: The CLI accepts a global --version entry

The CLI SHALL accept `--version` at the global position, before any command name, and SHALL report the acting CLI version without requiring a command and without contacting a Unity service. This entry SHALL be documented in top-level help alongside the other global options.

#### Scenario: Bare version query succeeds

- **WHEN** a caller invokes `unity-puer-exec --version` with no command
- **THEN** the CLI reports the version and does not emit a missing-command usage error

#### Scenario: Top-level help documents the entry

- **WHEN** a caller runs `unity-puer-exec --help`
- **THEN** the global options section documents `--version`

### Requirement: Machine-readable responses carry the acting CLI version

Every machine-readable CLI response SHALL include a top-level `cli_version` field, so a recorded transcript is sufficient to determine which CLI build produced the observed behavior.

#### Scenario: Every response family carries the field

- **WHEN** any formal command emits a success payload, an expected non-success payload, or an unexpected failure payload
- **THEN** the payload includes a top-level `cli_version` string

#### Scenario: Field survives response-file projection

- **WHEN** `--response-file` replaces the full payload with a compact reference
- **THEN** the compact reference retains `cli_version` alongside the existing routing fields
