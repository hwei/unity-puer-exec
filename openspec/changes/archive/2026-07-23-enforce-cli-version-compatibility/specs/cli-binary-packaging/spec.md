## MODIFIED Requirements

### Requirement: CLI is packaged as a single-file Windows executable

The CLI SHALL be packaged using PyInstaller `--onefile` mode with Python 3.12 on a Windows runner, producing a single `unity-puer-exec.exe`. The build SHALL stamp the package version from `packages/com.txcombo.unity-puer-exec/package.json` into the executable before packaging, and SHALL verify the stamp is present in the built artifact before that artifact is assembled into the published package tree.

#### Scenario: CI builds the CLI executable

- **WHEN** the GitHub Actions workflow builds the CLI
- **THEN** it produces a single file `unity-puer-exec.exe`
- **AND** the executable is built with PyInstaller `--onefile` using Python 3.12
- **AND** the executable includes all Python modules from `cli/python/` needed for CLI operation

#### Scenario: Build stamps the package version into the executable

- **WHEN** the workflow builds the CLI for a release
- **THEN** the version stamped into the executable equals the `version` field of `packages/com.txcombo.unity-puer-exec/package.json` at the built commit
- **AND** the stamped executable and the `package.json` published beside it in `CLI~/` declare the same version

#### Scenario: Build fails when the stamp is missing

- **WHEN** the built executable cannot report a stamped version
- **THEN** the workflow SHALL fail before assembling the UPM package tree
- **AND** no unstamped executable is published

#### Scenario: User runs the packaged executable

- **WHEN** a user or agent invokes `unity-puer-exec.exe` on a Windows system without Python installed
- **THEN** the executable runs successfully without requiring a separate Python installation
- **AND** the CLI behavior is identical to running the Python source directly
