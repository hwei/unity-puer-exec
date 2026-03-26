## Why

The Unity package and CLI are currently only usable from source checkout. Publishing to OpenUPM lets users install via `openupm add com.txcombo.unity-puer-exec` and get the CLI binary bundled in-package, eliminating the need to clone the repo or install Python.

## What Changes

- Supplement `package.json` with `license`, `repository`, and updated `author` fields required by OpenUPM.
- Add MIT `LICENSE` file to the package directory.
- Bundle the CLI as a PyInstaller `--onefile` Windows executable (`unity-puer-exec.exe`) inside a `CLI~/` hidden-asset folder, so Unity does not import it or generate `.meta` files.
- Add a GitHub Actions workflow (`release.yml`) that:
  - Triggers on `v*` tags pushed to `main`.
  - Builds the Windows exe using Python 3.12 + PyInstaller on a `windows-latest` runner.
  - Assembles a clean UPM package directory (Editor/, CLI~/, package.json, LICENSE).
  - Force-pushes the assembled tree to a `upm` branch and tags it `upm/v<version>`.
- Register the package on OpenUPM with `gitTagPrefix: upm/` pointing at the `upm` branch.

## Capabilities

### New Capabilities
- `openupm-release-pipeline`: CI workflow and package assembly for automated OpenUPM publishing via the upm-branch pattern.
- `cli-binary-packaging`: PyInstaller configuration and hidden-asset placement for shipping the CLI as a Windows executable inside the UPM package.

### Modified Capabilities
- `formal-cli-contract`: The CLI entry point gains binary distribution as `unity-puer-exec.exe`; the executable name and discovery path (package `CLI~/` folder) become part of the contract.

## Impact

- **package.json**: New fields (`license`, `repository`, `author.name` update).
- **New files**: `LICENSE`, `.github/workflows/release.yml`.
- **New branch**: `upm` (CI-managed, not for manual editing).
- **Git tags**: Dual-tag convention — `v*` on `main` (source), `upm/v*` on `upm` (release).
- **External dependency**: OpenUPM registry registration (one-time PR to `openupm/openupm`).
- **No runtime behavior change**: The C# Editor code and CLI logic are untouched.
