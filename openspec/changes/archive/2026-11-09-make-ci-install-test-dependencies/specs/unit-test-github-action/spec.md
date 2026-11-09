# Spec Delta

## ADDED Requirements

### Requirement: The unit-test workflow provisions every third-party dependency the selected suite imports

The repository's default unit-test workflow SHALL install the third-party packages that the
selected test modules import before running the suite, so that no selected test is skipped for a
missing dependency on the CI runner.

The set of test-time dependencies SHALL be expressed as a tracked repository artifact rather than
left implicit in whatever the runner image happens to provide.

#### Scenario: CI runs the full selected suite without dependency skips

- **WHEN the unit-test workflow runs on its configured runner
- **THEN it installs the tracked test dependencies before invoking the test command
- **AND** no selected test module reports a skip whose stated reason is a missing third-party import

#### Scenario: A new third-party import is covered by provisioning

- **WHEN a contributor adds a selected test that imports a third-party package
- **AND** adds that package to the tracked dependency artifact
- **THEN the workflow installs it and the test runs rather than skipping

### Requirement: A dependency-missing skip is not a silent pass in CI

A test that cannot run because a third-party dependency is unavailable SHALL fail, rather than
skip, when it executes in the CI environment. The same condition MAY skip outside CI, so a local
contributor without that dependency is not blocked.

#### Scenario: CI fails when a dependency is not provisioned

- **WHEN a selected test requires a third-party dependency that the workflow did not install
- **AND** the test executes in the CI environment
- **THEN the test fails with a message naming the missing dependency
- **AND** the workflow's result is a failure rather than a green check with a hidden skip

#### Scenario: A local run without the dependency still skips

- **WHEN the same test executes on a developer machine outside the CI environment
- **AND** the third-party dependency is unavailable
- **THEN the test skips with a message naming the missing dependency
- **AND** an optional dependency does not break an otherwise valid local run

#### Scenario: The CI environment is detected without extra contributor setup

- **WHEN a contributor runs the default suite locally
- **THEN no environment variable or configuration file must be set to obtain the local skip behavior
- **AND** the distinction between CI and non-CI execution comes from the CI provider's own
  environment rather than repository-local configuration
