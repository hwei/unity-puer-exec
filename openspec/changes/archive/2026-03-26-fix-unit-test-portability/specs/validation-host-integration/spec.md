## MODIFIED Requirements

### Requirement: Local package injection is the normal host wiring path

The validation host SHALL consume `com.txcombo.unity-puer-exec` through a local-only `manifest.json` injection. When the repository package root and host manifest share a filesystem anchor, the injected dependency SHALL use a reproducible relative `file:` path. When a Windows host manifest and repository package root are on different volumes, repository-owned helper tooling MUST emit a deterministic non-relative `file:` path instead of failing to rewrite the manifest.

#### Scenario: Host is wired to local package on the same filesystem anchor

- **WHEN** a contributor prepares the validation host for package testing and the manifest location can express the package root as a relative path
- **THEN** `Project/Packages/manifest.json` references the local package path using a reproducible relative `file:` dependency
- **AND** the repository documents or automates that wiring through a repository-owned helper workflow
- **AND** the manifest change is treated as local validation setup rather than normal host source control workflow

#### Scenario: Host manifest and package root are on different Windows volumes

- **WHEN** repository-owned helper tooling computes the local package dependency for a validation-host manifest on a different Windows volume from the repository package root
- **THEN** the helper emits a deterministic `file:` dependency value for the formal package
- **AND** the helper does not fail only because a relative path cannot be formed across volumes
