## ADDED Requirements

### Requirement: Local helper prepares an OpenUPM source release
The repository SHALL provide a local maintainer helper that prepares an OpenUPM source release by validating repository state, updating `packages/com.txcombo.unity-puer-exec/package.json` to a requested version, and running the default mocked/unit release test suite before any source release tag is created.

#### Scenario: Maintainer prepares a new version successfully
- **WHEN** a maintainer runs the release helper with a target version on a clean repository state
- **THEN** the helper validates the repository preconditions needed for a source release
- **AND** the helper updates `packages/com.txcombo.unity-puer-exec/package.json` to the requested version
- **AND** the helper runs the repository's default mocked/unit release test suite
- **AND** the helper reports the next manual publish steps after preparation succeeds

### Requirement: Local helper rejects unsafe release preparation state
The release helper SHALL refuse to continue when local repository state makes a source release preparation unsafe, including a dirty working tree or an already existing local or remote `v<version>` tag.

#### Scenario: Working tree is dirty
- **WHEN** a maintainer runs the release helper while the repository has uncommitted changes
- **THEN** the helper stops without changing `package.json`
- **AND** the helper explains that release preparation requires a clean working tree

#### Scenario: Requested tag already exists
- **WHEN** a maintainer runs the release helper for version `0.1.0` and tag `v0.1.0` already exists locally or on the remote
- **THEN** the helper stops without changing `package.json`
- **AND** the helper reports that the requested release tag is already reserved

### Requirement: Local helper supports optional commit and tag creation
The release helper SHALL support optional creation of a local release commit and a local `v<version>` source tag, and it SHALL require committed release state before creating the tag.

#### Scenario: Maintainer requests commit and tag creation
- **WHEN** a maintainer runs the release helper with options to create both a release commit and a source tag
- **THEN** the helper creates a local commit for the prepared release state after successful validation and tests
- **AND** the helper creates a local `v<version>` tag pointing at that commit
- **AND** the helper does not push the commit or tag to the remote

#### Scenario: Maintainer requests tag without committed release state
- **WHEN** a maintainer requests source tag creation but the prepared release version is not yet committed
- **THEN** the helper refuses to create the tag
- **AND** the helper explains that tag creation requires committed release state

### Requirement: Local helper provides a no-side-effect dry run
The release helper SHALL support a `--dry-run` mode that reports the intended version update, validations, tests, and optional git actions without modifying repository state or executing the test suite.

#### Scenario: Maintainer previews a release plan
- **WHEN** a maintainer runs the release helper with `--dry-run`
- **THEN** the helper reports the current version and requested version
- **AND** the helper reports which validations and tests would run
- **AND** the helper reports whether it would create a commit or tag
- **AND** the helper does not modify `package.json`
- **AND** the helper does not create a commit or tag
- **AND** the helper does not run the release test suite

### Requirement: Real-host validation remains opt-in
The release helper SHALL keep environment-dependent real-host integration coverage as an explicit opt-in path rather than part of the default release preparation flow.

#### Scenario: Maintainer runs default release preparation
- **WHEN** a maintainer runs the release helper without requesting real-host coverage
- **THEN** the helper runs only the default mocked/unit release test suite
- **AND** the helper does not require Unity host prerequisites to be present

#### Scenario: Maintainer opts into real-host validation
- **WHEN** a maintainer runs the release helper with the explicit real-host validation option
- **THEN** the helper includes the repository's real-host integration test command in the release preparation flow
- **AND** any failure in that opt-in validation stops release preparation
