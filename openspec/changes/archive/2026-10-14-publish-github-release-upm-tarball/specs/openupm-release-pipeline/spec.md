## ADDED Requirements

### Requirement: Release workflow packs an installable UPM tarball

The release workflow SHALL produce a UPM package tarball from the same assembled package tree that
it pushes to the `upm` branch, using `npm pack` semantics, and SHALL name it
`com.txcombo.unity-puer-exec-<version>.tgz`. The tarball SHALL be written outside the staged package
tree so it is not included in the `upm` branch content.

#### Scenario: A version tag triggers the release workflow

- **WHEN** a maintainer pushes a `v<version>` tag that matches `package.json`
- **THEN** the workflow packs the assembled package tree into `com.txcombo.unity-puer-exec-<version>.tgz`
- **AND** the tarball is written to a directory outside the staged package tree
- **AND** the `upm` branch content does not contain the tarball

#### Scenario: Packing fails to produce the expected file

- **WHEN** the pack step does not produce `com.txcombo.unity-puer-exec-<version>.tgz`
- **THEN** the workflow fails instead of proceeding to create the release

### Requirement: UPM tarball contains the complete package

The UPM tarball SHALL contain the complete package tree, including the built CLI executable under
`CLI~`, so that the executable is distributed together with the Unity package that hosts it.

#### Scenario: User inspects the release tarball

- **WHEN** a user downloads the release tarball
- **THEN** the tarball contains `Editor/`, `CLI~/unity-puer-exec.exe`, `package.json`, `LICENSE`, and `README.md`
- **AND** the tarball is installable by Unity Package Manager as a package tarball

### Requirement: Release workflow creates a GitHub Release with the tarball asset

The release workflow SHALL create a GitHub Release for the pushed `v<version>` tag and attach the
UPM tarball as a release asset. The Release SHALL use generated release notes. The workflow SHALL
keep the OpenUPM registration and `upm` branch publishing behavior unchanged.

#### Scenario: Maintainer pushes a version tag

- **WHEN** a maintainer pushes a `v<version>` tag
- **THEN** a GitHub Release exists for that tag
- **AND** the Release body contains generated release notes
- **AND** the Release has `com.txcombo.unity-puer-exec-<version>.tgz` attached as an asset
- **AND** the workflow still force-pushes the assembled tree to the `upm` branch and creates the `upm/v<version>` tag

#### Scenario: Workflow is re-run for an existing release

- **WHEN** the release workflow runs again for a tag whose GitHub Release already exists
- **THEN** the workflow uploads or replaces the tarball asset without failing
