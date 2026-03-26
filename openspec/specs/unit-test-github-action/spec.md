# unit-test-github-action Specification

## Purpose
TBD - created by archiving change add-unit-test-github-action. Update Purpose after archive.
## Requirements
### Requirement: Repository provides a default automated unit-test workflow
The repository SHALL provide a GitHub Actions workflow that runs the mocked/unit Python test suite for normal development changes without requiring Unity Editor or a validation-host project.

#### Scenario: Pull request triggers automated unit tests
- **WHEN** a contributor opens or updates a pull request against the repository
- **THEN** GitHub Actions runs the repository's default automated unit-test workflow
- **AND** the workflow executes on a GitHub-hosted runner without Unity-specific machine prerequisites

### Requirement: Automated unit-test selection is explicit
The repository SHALL define the automated unit-test command or file set explicitly so the default GitHub Actions workflow excludes real-host integration coverage by configuration rather than by runtime skip behavior.

#### Scenario: CI selects the default unit-test suite
- **WHEN** the GitHub Actions unit-test workflow starts the repository-owned test command
- **THEN** the selected suite includes mocked CLI, runtime, packaging, OpenSpec, and validation-host helper tool tests
- **AND** the selected suite excludes `tests/test_real_host_integration.py`
- **AND** a reader can determine the intended unit-test boundary from repository-owned workflow or test-runner configuration

### Requirement: Validation-host helper test names distinguish tool logic from real-host integration
Repository-owned tests for validation-host helper scripts SHALL use names that identify them as tool-logic coverage rather than real Unity runtime integration.

#### Scenario: Contributor scans test files
- **WHEN** a contributor or agent reviews the `tests/` directory or CI selection list
- **THEN** the prepare/cleanup validation-host helper tests are named with a `*_tool.py` suffix
- **AND** their names do not imply that Unity Editor is required to run them

