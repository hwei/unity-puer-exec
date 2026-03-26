# openupm-release-pipeline Specification

## Purpose
TBD - created by archiving change publish-to-openupm. Update Purpose after archive.
## Requirements
### Requirement: GitHub Actions workflow builds and publishes on version tag

The repository SHALL include a GitHub Actions workflow that triggers on `v*` tag pushes to `main`. The workflow SHALL build the CLI executable, assemble a clean UPM package tree, force-push it to a `upm` branch, and create a `upm/v<version>` tag on that branch.

#### Scenario: Maintainer pushes a version tag

- **WHEN** a maintainer pushes a tag matching `v*` (e.g., `v0.1.0`) to `main`
- **THEN** the GitHub Actions workflow triggers automatically
- **AND** the workflow builds the CLI Windows executable
- **AND** the workflow assembles a package tree containing only Editor/, CLI~/, package.json, and LICENSE
- **AND** the workflow force-pushes the assembled tree to the `upm` branch
- **AND** the workflow creates a `upm/v<version>` tag on the `upm` branch

#### Scenario: Assembled package tree contains no development artifacts

- **WHEN** the CI workflow assembles the UPM package tree for the `upm` branch
- **THEN** the tree does NOT contain tests/, tools/, openspec/, cli/python/, .github/, or any other development-only content
- **AND** the tree contains exactly the files needed for a functional UPM package installation

### Requirement: Version consistency between package.json and git tags

The CI workflow SHALL extract the version from `packages/com.txcombo.unity-puer-exec/package.json` and verify it matches the pushed tag before proceeding with the release.

#### Scenario: Tag version matches package.json version

- **WHEN** tag `v0.2.0` is pushed and package.json contains `"version": "0.2.0"`
- **THEN** the workflow proceeds with building and publishing

#### Scenario: Tag version does not match package.json version

- **WHEN** tag `v0.2.0` is pushed but package.json contains a different version
- **THEN** the workflow fails with a clear error message indicating the mismatch
- **AND** no changes are pushed to the `upm` branch

### Requirement: OpenUPM registration uses upm branch and tag prefix

The package SHALL be registered on OpenUPM with `gitTagPrefix: upm/` pointing at the `upm` branch so that OpenUPM only picks up CI-assembled release tags.

#### Scenario: OpenUPM detects a new release

- **WHEN** the CI workflow creates tag `upm/v0.1.0` on the `upm` branch
- **THEN** OpenUPM detects and publishes version `0.1.0` of `com.txcombo.unity-puer-exec`

### Requirement: package.json includes required OpenUPM metadata

The package.json SHALL include `license`, `repository`, `author`, and `dependencies` fields in addition to existing fields. The `author.name` SHALL be `Will Huang`. The `license` SHALL be `MIT`. The `dependencies` SHALL declare `com.tencent.puerts.core` at minimum version `3.0.0`.

#### Scenario: OpenUPM validates package metadata

- **WHEN** OpenUPM ingests the package from the `upm` branch
- **THEN** the package.json contains a valid `license` field set to `MIT`
- **AND** the package.json contains a `repository` field pointing to the GitHub repo
- **AND** the package.json contains `author.name` set to `Will Huang`
- **AND** the package.json contains `dependencies` with `com.tencent.puerts.core` at `3.0.0`

### Requirement: MIT LICENSE file is included in the published package

The published UPM package tree SHALL include a LICENSE file containing the MIT license text.

#### Scenario: User inspects the installed package license

- **WHEN** a user installs the package via OpenUPM and inspects the package directory
- **THEN** a LICENSE file is present at the package root with valid MIT license text

