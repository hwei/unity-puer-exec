## Why

The repository currently publishes releases through GitHub Actions but does not automatically verify the mocked Python test suite on pull requests or branch pushes. That leaves routine contract regressions undiscovered until a maintainer runs tests locally and makes the test boundary between mocked and real-host coverage harder to understand.

## What Changes

- Add a GitHub Actions workflow that runs the repository's mocked/unit test suite on normal development events without requiring Unity Editor.
- Define the CI test selection explicitly so the workflow excludes real-host integration coverage instead of relying on runtime skips.
- Rename the validation-host helper test modules to make it obvious they cover local tool logic rather than real Unity Editor integration.
- Document the automated unit-test workflow and its boundary relative to real-host validation.

## Capabilities

### New Capabilities
- `unit-test-github-action`: Define the repository-owned GitHub Actions workflow and test selection contract for mocked/unit test automation.

### Modified Capabilities
- `validation-host-integration`: Clarify that real-host validation remains a separate workflow surface and is not part of the default automated unit-test action.

## Impact

- Adds a new GitHub Actions workflow under `.github/workflows/`.
- Updates repository test naming and test-selection commands under `tests/`.
- Extends OpenSpec documentation for automated unit-test coverage versus real-host validation coverage.
