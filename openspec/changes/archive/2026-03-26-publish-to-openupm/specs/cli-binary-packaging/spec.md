## ADDED Requirements

### Requirement: CLI is packaged as a single-file Windows executable

The CLI SHALL be packaged using PyInstaller `--onefile` mode with Python 3.12 on a Windows runner, producing a single `unity-puer-exec.exe`.

#### Scenario: CI builds the CLI executable

- **WHEN** the GitHub Actions workflow builds the CLI
- **THEN** it produces a single file `unity-puer-exec.exe`
- **AND** the executable is built with PyInstaller `--onefile` using Python 3.12
- **AND** the executable includes all Python modules from `cli/python/` needed for CLI operation

#### Scenario: User runs the packaged executable

- **WHEN** a user or agent invokes `unity-puer-exec.exe` on a Windows system without Python installed
- **THEN** the executable runs successfully without requiring a separate Python installation
- **AND** the CLI behavior is identical to running the Python source directly

### Requirement: CLI executable is placed in a hidden asset directory

The CLI executable SHALL reside in a `CLI~/` directory at the UPM package root. The `~` suffix ensures Unity does not import the directory or generate `.meta` files for its contents.

#### Scenario: Unity imports the installed package

- **WHEN** Unity imports the package installed via OpenUPM
- **THEN** Unity does not generate `.meta` files for the `CLI~/` directory or its contents
- **AND** Unity does not attempt to import or compile the executable

#### Scenario: Agent discovers the CLI executable in a Unity project

- **WHEN** an agent searches for `unity-puer-exec.exe` within a Unity project directory
- **THEN** the executable is found at `Library/PackageCache/com.txcombo.unity-puer-exec@<version>/CLI~/unity-puer-exec.exe`
