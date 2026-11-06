# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
