# Spec Delta

## ADDED Requirements

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
