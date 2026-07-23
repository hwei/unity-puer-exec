# cli-version-compatibility Specification

## Purpose
TBD - created by archiving change enforce-cli-version-compatibility. Update Purpose after archive.
## Requirements
### Requirement: The CLI resolves its own version

The CLI SHALL resolve a version string identifying the package release it belongs to. A frozen executable SHALL resolve it from a version stamped into the binary at build time. A source invocation SHALL resolve it from `packages/com.txcombo.unity-puer-exec/package.json` in the source tree.

#### Scenario: Frozen executable resolves its stamped version

- **WHEN** a packaged `unity-puer-exec.exe` resolves its version
- **THEN** the resolved value is the version stamped into the binary at build time
- **AND** the CLI does not consult any `package.json` on the invoking machine to determine its own version

#### Scenario: Source invocation resolves the source-tree version

- **WHEN** the CLI is invoked from `cli/python/unity_puer_exec.py` in the source tree
- **THEN** the resolved value is the `version` field of `packages/com.txcombo.unity-puer-exec/package.json`

#### Scenario: Frozen executable without a stamp refuses to act

- **WHEN** a frozen executable cannot resolve a stamped version
- **THEN** the CLI SHALL treat the build as unverifiable
- **AND** commands SHALL return `version_mismatch` with a guard value of `cli_version_unknown`
- **AND** the CLI SHALL NOT fall back to reading a `package.json` from the invoking machine

### Requirement: The Unity bridge reports its package version

The Unity control service SHALL include a `bridge_version` field in its `/health` response, resolved from the Unity package metadata for the assembly that provides the service.

#### Scenario: Health response on a package-installed bridge

- **WHEN** a caller probes `/health` on a ready service whose Editor assembly belongs to an installed package
- **THEN** the response includes `bridge_version` set to that package's version

#### Scenario: Bridge assembly does not belong to a package

- **WHEN** the Editor assembly providing the service does not belong to an installed Unity package
- **THEN** the health response SHALL omit `bridge_version` or report it as null rather than reporting a guessed value

### Requirement: CLI responses carry the acting CLI version

Every machine-readable CLI response SHALL include a top-level `cli_version` field naming the CLI build that produced it, on success and non-success payloads alike, so that the acting build is recoverable from a transcript without a separate query.

#### Scenario: Success response names the acting build

- **WHEN** any command returns a success payload
- **THEN** the payload includes a top-level `cli_version` string

#### Scenario: Non-success response names the acting build

- **WHEN** any command returns an expected non-success payload or an unexpected failure payload
- **THEN** the payload includes a top-level `cli_version` string

#### Scenario: Response-file reference names the acting build

- **WHEN** a command is invoked with `--response-file` and emits a compact reference instead of the full payload
- **THEN** the compact reference includes `cli_version`

### Requirement: The CLI reports its version without a command

The CLI SHALL accept `--version` at the global position and report the resolved CLI version without requiring a command argument and without contacting any Unity service.

#### Scenario: Version query without a command

- **WHEN** a caller invokes `unity-puer-exec --version`
- **THEN** the CLI reports the resolved version
- **AND** the invocation does not fail with a missing-command usage error
- **AND** no Unity service is contacted

#### Scenario: Version and help entries are not subject to the guards

- **WHEN** a caller invokes `--version`, `--help`, `--help-args`, or `--help-status` on an installation that would fail either version guard
- **THEN** the entry still reports its content rather than returning `version_mismatch`
- **AND** a frozen build with no stamped version reports the unknown state through `--version` rather than refusing to answer

#### Scenario: Diagnostic entries remain usable after a refusal

- **WHEN** a command has returned `version_mismatch` and the caller follows the response guidance to confirm the acting build
- **THEN** the recommended `--version` invocation succeeds

### Requirement: The CLI verifies its version against an adjacent installed package

When the CLI executable resolves to a location inside an installed package tree, the CLI SHALL compare its own version against the `version` field of that package's `package.json` before performing command work.

#### Scenario: Executable version disagrees with its containing package

- **WHEN** the executable is invoked from `<package>/CLI~/unity-puer-exec.exe` and its resolved version differs from the `version` in `<package>/package.json`
- **THEN** the command SHALL return `version_mismatch` with a guard value of `package_layout`
- **AND** the response SHALL name both versions and the package path
- **AND** the check SHALL complete without contacting any Unity service

#### Scenario: Executable is not inside a package tree

- **WHEN** the executable is invoked from a location that does not resolve to an installed package tree
- **THEN** the package-layout guard SHALL be skipped rather than reported as a mismatch

### Requirement: The CLI verifies its version against the control service

Every command that contacts the Unity control service SHALL compare the CLI version against the `bridge_version` reported by that service before performing the command's work, in both `--project-path` and `--base-url` mode.

#### Scenario: Bridge version disagrees with CLI version

- **WHEN** a command obtains a health response whose `bridge_version` differs from the CLI version
- **THEN** the command SHALL return `version_mismatch` with a guard value of `bridge`
- **AND** the response SHALL name both versions and the control endpoint
- **AND** the command SHALL NOT execute scripts, start observation, or otherwise perform its work

#### Scenario: Guard applies in direct base-url mode

- **WHEN** a command targets a service through `--base-url` and the reported `bridge_version` differs from the CLI version
- **THEN** the command SHALL return `version_mismatch` on the same terms as project-scoped mode

### Requirement: Version comparison uses exact equality

The CLI SHALL compare version strings for exact equality. The CLI SHALL NOT apply semantic-version range logic, minor-level tolerance, or a maintained compatibility table.

#### Scenario: Versions differing only in patch level are a mismatch

- **WHEN** the CLI version and the counterpart version differ in any component
- **THEN** the comparison result is a mismatch

#### Scenario: Identical versions pass

- **WHEN** the CLI version and the counterpart version are identical strings
- **THEN** the comparison result is a match and the command proceeds

### Requirement: An unavailable counterpart version is a mismatch

When a counterpart does not report a version, the CLI SHALL treat the condition as a mismatch rather than as an unverified pass, because a counterpart that cannot state its version predates or falls outside this contract.

#### Scenario: Bridge reports no version

- **WHEN** a health response omits `bridge_version` or reports it as null
- **THEN** the command SHALL return `version_mismatch`
- **AND** the reported counterpart version SHALL be null
- **AND** the guard value SHALL distinguish this case from a genuine version difference

### Requirement: A version mismatch refuses command work and offers no bypass

A `version_mismatch` result SHALL be terminal for the invocation: the command SHALL NOT perform its work, and the CLI SHALL NOT provide a caller-facing flag, environment variable, or other documented mechanism that permits a mismatched pair to proceed.

#### Scenario: Mismatch prevents execution

- **WHEN** `exec` detects a version mismatch
- **THEN** no script is executed and no exec request is accepted
- **AND** the response reports `version_mismatch`

#### Scenario: No documented bypass exists

- **WHEN** a caller consults CLI help for a way to proceed despite a version mismatch
- **THEN** help SHALL describe reconciling the installation as the resolution
- **AND** help SHALL NOT document any flag or setting that suppresses the guard

