# unit-test-github-action Specification

## Purpose
Provide a GitHub Actions workflow that runs the repository's default mocked/unit Python test suite for routine development changes without requiring Unity Editor or a validation-host project.

## Requirements

### Requirement: Repository provides a default automated unit-test workflow
The repository SHALL provide a GitHub Actions workflow that runs the mocked/unit Python test suite for normal development changes without requiring Unity Editor or a validation-host project.

#### Scenario: Pull request triggers automated unit tests
- **WHEN** a contributor opens or updates a pull request against the repository
- **THEN** GitHub Actions runs the repository's default automated unit-test workflow
- **AND** the workflow executes on a GitHub-hosted runner without Unity-specific machine prerequisites

### Requirement: Automated unit-test selection is explicit
The repository SHALL define the automated unit-test command or file set explicitly so the default GitHub Actions workflow excludes real-host integration coverage by configuration rather than by runtime skip behavior. The explicitly selected set SHALL be the same set as the default suite the repository documents for local runs, so that CI and the documented command line cannot drift apart.

#### Scenario: CI selects the default unit-test suite
- **WHEN** the GitHub Actions unit-test workflow starts the repository-owned test command
- **THEN** the selected suite includes mocked CLI, runtime, packaging, OpenSpec, and validation-host helper tool tests
- **AND** the selected suite excludes `tests/test_real_host_integration.py`
- **AND** a reader can determine the intended unit-test boundary from repository-owned workflow or test-runner configuration

#### Scenario: The documented default suite matches the CI selection
- **WHEN** a contributor compares the module list in the repository's documented default-suite command line with the module arguments in the unit-test workflow
- **THEN** the two lists name the same set of test modules
- **AND** no mocked-layer module appears in one list and not the other

#### Scenario: A mocked module that imports the real-host suite still belongs in CI
- **WHEN** a test module imports `tests/test_real_host_integration.py` in order to drive its helpers under `unittest.mock`
- **AND** that module itself requires no Unity Editor and no validation host
- **THEN** the module belongs in the CI selection and in the documented default suite
- **AND** its presence does not violate the exclusion of `tests/test_real_host_integration.py` itself, which is excluded as a selected module, not as an import

### Requirement: Validation-host helper test names distinguish tool logic from real-host integration
Repository-owned tests for validation-host helper scripts SHALL use names that identify them as tool-logic coverage rather than real Unity runtime integration.

#### Scenario: Contributor scans test files
- **WHEN** a contributor or agent reviews the `tests/` directory or CI selection list
- **THEN** the prepare/cleanup validation-host helper tests are named with a `*_tool.py` suffix
- **AND** their names do not imply that Unity Editor is required to run them

### Requirement: Default unit tests do not require repository-local Unity project configuration

The repository SHALL keep the default GitHub Actions unit-test suite independent from repository-local `.env` contents and process-level `UNITY_PROJECT_PATH` configuration.

#### Scenario: GitHub-hosted unit tests run without Unity project configuration

- **WHEN** the default `Unit Tests` workflow runs on a GitHub-hosted runner without `.env` and without `UNITY_PROJECT_PATH`
- **THEN** the selected unit tests complete without failing on missing real-project configuration
- **AND** any Unity-project-dependent validation remains outside the default unit-test workflow boundary

### Requirement: A disagreement between the two default-suite lists fails the default suite

The repository SHALL own a mocked-layer test that reads the default-suite module list from the
unit-test workflow and from the documented local command line and asserts the two are the same
set. A module present in one list and absent from the other SHALL fail that test, so the drift
is reported by the suite it narrows rather than discovered by a reader.

#### Scenario: A module is added to the documented list only

- **WHEN** a contributor adds a new test module to the documented default-suite command line
- **AND** does not add it to the unit-test workflow's module arguments
- **THEN** the mocked-layer comparison test fails
- **AND** the failure names the module that is present in only one list

#### Scenario: A module is added to CI only

- **WHEN** a contributor adds a new test module to the unit-test workflow
- **AND** does not add it to the documented default-suite command line
- **THEN** the mocked-layer comparison test fails
- **AND** the failure names the module that is present in only one list

#### Scenario: The comparison reads the lists as they are written

- **WHEN** the comparison test resolves the two lists
- **THEN** it parses the unit-test workflow's module arguments and the documented command line directly
- **AND** it does not consult a third representation that would itself need keeping in sync

### Requirement: The default suite selects every mocked-layer test module or excludes it by name

The repository SHALL select every mocked-layer test module in `tests/test_*.py` into both the
default-suite lists. A module that is not selected SHALL appear in an explicit exclusion list that
states why it cannot run in the default suite, so that a module which is absent from both lists
fails the guard by name rather than not running.

#### Scenario: A new module added to neither list fails the guard

- **WHEN a contributor adds a `tests/test_*.py` module that needs no Unity Editor and no
  validation host
- **AND** adds it to neither the documented default suite nor the unit-test workflow
- **THEN a mocked-layer guard fails
- **AND** its message names the module and the two lists it is missing from

#### Scenario: A module that needs the real host is excluded by name with a reason

- **WHEN a `tests/test_*.py` module can run only against a live Unity Editor and a prepared
  validation host
- **THEN it is absent from both default-suite lists
- **AND** it is named in the guard's exclusion list together with the reason it cannot run there
- **AND** the guard passes

#### Scenario: The selection stays complete as the directory grows

- **WHEN a contributor adds a new mocked-layer module and selects it in both lists
- **THEN the guard passes without the exclusion list changing
- **AND** no extra bookkeeping is required beyond the two list edits the repository already
  requires

#### Scenario: An exclusion without a stated reason is not expressible

- **WHEN the exclusion list names a module
- **THEN it also carries a non-empty reason string
- **AND** a bare module name with no reason fails the guard
