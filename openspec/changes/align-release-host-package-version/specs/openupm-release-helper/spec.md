# Spec Delta

## Purpose

Make the release helper prove that the validation host would load the release candidate package before it spends a real-host suite run, report a version identity mismatch as one diagnosis instead of many test failures, and align the host version only when asked and only when the host's package content matches this repository.

## ADDED Requirements

### Requirement: Real-host validation requires the host-loaded package version to match the release candidate

When real-host validation is requested, the release helper SHALL resolve the validation host the same way the real-host suite does, determine which package tree that host will load, and establish that the loaded tree is the release candidate before writing the repository version and before executing the default unit suite or the real-host suite. The helper SHALL refuse to continue when the host cannot be resolved or when the loaded package is not the release candidate.

#### Scenario: Validation host cannot be resolved

- **WHEN** a maintainer requests real-host validation
- **AND** the validation host path is unset, does not exist, or has no `Packages/manifest.json`
- **THEN** the helper stops before writing the repository version and before running any test
- **AND** the result states that real-host validation was requested but no usable host is available, instead of recording the real-host suite as run

#### Scenario: Host loads an embedded copy that lags the release candidate

- **WHEN** a maintainer requests real-host validation for version `0.12.0`
- **AND** the host's `Packages/` contains an immediate child whose `package.json` declares the formal package name with version `0.11.0`
- **THEN** the helper stops before writing the repository version and before running any test
- **AND** the result names the loaded package path, the expected version, and the observed version
- **AND** the result offers both remedies: align the host copy, or remove the embedded copy so the `file:` dependency wins

#### Scenario: Host loads the repository package through the file dependency

- **WHEN** the host has no embedded package declaring the formal name
- **AND** its manifest declares the formal package with a `file:` value resolving to this repository's package root
- **THEN** the helper treats the loaded package as the release candidate by identity of path, without comparing against the repository version that has not yet been bumped
- **AND** the helper proceeds without writing to the host

#### Scenario: An Editor is already running for the host

- **WHEN** the host's loaded package is the release candidate
- **AND** an Editor launched before the release run is still open for that host and reports an older `bridge_version`
- **THEN** the helper does not refuse on that basis, because the real-host suite closes the running Editor and launches a fresh one before validating

#### Scenario: Host is not wired to the package

- **WHEN** the host has no embedded package declaring the formal name and no usable manifest entry for it
- **THEN** the helper stops with a not-wired result instead of validating a package the host does not load

#### Scenario: More than one embedded copy declares the package name

- **WHEN** two or more immediate children of the host's `Packages/` declare the formal package name
- **THEN** the helper stops with an ambiguous result that names every such directory

### Requirement: Host version alignment is opt-in and guarded by package content parity

The release helper SHALL write the release candidate version into the host's loaded package only when the maintainer requests alignment explicitly, and only when that package's content matches this repository's package content across the whole package tree except `CLI~/`. Content comparison SHALL ignore the `package.json` `version` field and line-ending differences in text files. Alignment SHALL change only the `version` field.

#### Scenario: Maintainer requests alignment for a content-identical host copy

- **WHEN** a maintainer requests real-host validation together with host alignment
- **AND** the host's loaded package has the same relative path set and file contents as this repository's package, ignoring `CLI~/`, the version field, and line-ending differences
- **THEN** the helper writes the release candidate version into that copy's `package.json`
- **AND** every other field and byte of the file is preserved
- **AND** the alignment is recorded in the helper's executed actions

#### Scenario: Host copy differs only in line endings

- **WHEN** a maintainer requests alignment
- **AND** the host copy's text files differ from this repository's package only by CRLF versus LF line endings
- **THEN** the helper treats the content as matching and aligns the version

#### Scenario: Repository package gains a directory the host copy lacks

- **WHEN** a maintainer requests alignment
- **AND** this repository's package contains files under a top-level directory that is absent from the host copy
- **THEN** the helper reports those files as differences and refuses

#### Scenario: Host copy content diverges from the repository package

- **WHEN** a maintainer requests alignment and the host copy differs in content from this repository's package
- **THEN** the helper refuses before writing and before running any test
- **AND** the result names the differing paths and states that the host copy must be synced or removed

#### Scenario: Alignment is not requested

- **WHEN** a maintainer requests real-host validation without host alignment
- **THEN** the helper never writes to the host project

### Requirement: Host version alignment is reverted when release preparation rolls back

When release preparation fails or is interrupted after host alignment and before the release commit, the helper SHALL restore the host `package.json` it modified to its original bytes and restore the repository package version, so the host stays consistent with the repository version that is left behind.

#### Scenario: A test suite fails after alignment

- **WHEN** host alignment succeeded and the unit or real-host suite then fails
- **THEN** the helper restores the host `package.json` to its pre-alignment bytes
- **AND** the helper restores the repository package version as it does today

#### Scenario: Maintainer interrupts the run after alignment

- **WHEN** host alignment succeeded and the maintainer interrupts the helper while a test suite is running
- **THEN** the helper restores the host `package.json` to its pre-alignment bytes and restores the repository package version before exiting

#### Scenario: Release preparation succeeds

- **WHEN** alignment succeeded and the release commit and tag are created
- **THEN** the helper leaves the host copy at the release candidate version

### Requirement: Dry run reports host package identity without mutating the host

The release helper's dry-run mode SHALL report the resolved host, the loaded package path, the observed version, and whether an alignment request would be permitted by the parity check, without writing to the host project.

#### Scenario: Maintainer previews a release with real-host validation

- **WHEN** a maintainer runs the helper with dry run and real-host validation requested
- **THEN** the result reports the loaded package path, how it was identified, and the versions compared
- **AND** the result reports the parity verdict when alignment was requested
- **AND** the host `package.json` and the repository `package.json` are unchanged
