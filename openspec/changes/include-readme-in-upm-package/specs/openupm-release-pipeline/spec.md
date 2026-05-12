## MODIFIED Requirements

### Requirement: GitHub Actions workflow builds and publishes on version tag

The repository SHALL include a GitHub Actions workflow that triggers on `v*` tag pushes to `main`. The workflow SHALL build the CLI executable, assemble a clean UPM package tree, force-push it to a `upm` branch, and create a `upm/v<version>` tag on that branch.

#### Scenario: Maintainer pushes a version tag

- **WHEN** a maintainer pushes a tag matching `v*` (e.g., `v0.1.0`) to `main`
- **THEN** the GitHub Actions workflow triggers automatically
- **AND** the workflow builds the CLI Windows executable
- **AND** the workflow assembles a package tree containing only the publishable package assets: `Editor/`, `CLI~/`, `package.json`, `LICENSE`, `README.md`, and the committed `.meta` siblings required for Unity-imported assets outside `CLI~/`
- **AND** the workflow force-pushes the assembled tree to the `upm` branch
- **AND** the workflow creates a `upm/v<version>` tag on the `upm` branch

#### Scenario: Assembled package tree contains no development artifacts

- **WHEN** the CI workflow assembles the UPM package tree for the `upm` branch
- **THEN** the tree does NOT contain tests/, tools/, openspec/, cli/python/, .github/, or any other development-only content
- **AND** the tree contains exactly the files needed for a functional UPM package installation, including `README.md` and committed `.meta` files for Unity-imported package assets outside `CLI~/`

## ADDED Requirements

### Requirement: README.md is included in the published package tree

The published UPM package tree SHALL include a `README.md` file at the package root. The file SHALL be a copy of the repository root `README.md` and SHALL be included in the CI assembly step.

#### Scenario: User inspects the installed package README

- **WHEN** a user installs the package via OpenUPM and inspects the package directory
- **THEN** a `README.md` file is present at the package root

#### Scenario: CI workflow assembles the package tree

- **WHEN** the CI workflow assembles the UPM package tree
- **THEN** the assembly step copies `README.md` from `packages/com.txcombo.unity-puer-exec/README.md` into the staged package tree

### Requirement: package.json includes readme field for Unity Package Manager UI

The package.json SHALL include a `"readme"` field whose value is `"README.md"`. This enables Unity Package Manager (2020.3+) to render the README content in the Package Manager details pane.

#### Scenario: Unity Package Manager displays the README

- **WHEN** a user selects the package in Unity Package Manager
- **THEN** the details pane renders the README content from the path specified in the `"readme"` field
