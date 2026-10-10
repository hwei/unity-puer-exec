# Spec Delta

## Purpose

Give the Unity package a fast, in-Editor unit-test surface for pure server-side behavior, so response-construction and job-state regressions are caught without the live-Editor real-host suite.

## ADDED Requirements

### Requirement: Package server behavior has an EditMode test assembly

The package SHALL include an EditMode test assembly under `Tests/EditMode/` with an assembly
definition constrained to the Editor test platform. The definition SHALL reference the
package Editor assembly and the Unity test framework, and SHALL be gated by the test
framework's include constraint so it never enters a player build.

#### Scenario: EditMode test assembly is present and scoped to the Editor

- **WHEN** the package tree is inspected
- **THEN** `Tests/EditMode/` contains an assembly definition
- **AND** the definition is restricted to the Editor test platform
- **AND** it references the package Editor assembly and the Unity test framework

#### Scenario: The default unit-test workflow does not require Unity

- **WHEN** the repository's default Python unit-test suite runs on a machine with no Unity Editor
- **THEN** it completes without running the EditMode tests
- **AND** it still passes

### Requirement: EditMode tests cover refresh-block retention and replay

The EditMode tests SHALL cover the server-side refresh-block retention and replay behavior: a
play-mode suppression is retained on the job and replayed by the terminal response builder,
other refresh outcomes are not replayed, and retained state does not leak between jobs.

#### Scenario: A play-mode suppression is retained and replayed

- **WHEN** a job's refresh was suppressed by play mode and the refresh block is retained
- **AND** the terminal response builder renders that snapshot
- **THEN** the response carries the retained refresh block
- **AND** the block names play mode as the skip reason

#### Scenario: Other refresh outcomes are not replayed

- **WHEN** a job's refresh was triggered rather than suppressed by play mode
- **THEN** its terminal snapshot carries no retained refresh block
- **AND** the terminal response builder renders no refresh block for it

#### Scenario: Retention does not leak between jobs

- **WHEN** one job retains a play-mode refresh block
- **AND** a different job reaches a terminal state without one
- **THEN** the second job's terminal response carries no refresh block

### Requirement: The EditMode harness runs without the real-host CLI flow

The repository SHALL document a repository-local command that runs the EditMode tests in Unity
batch mode without launching the CLI real-host suite. This harness SHALL remain outside the
default Python unit-test workflow, and the real-host play-mode case SHALL remain as the
end-to-end backstop. The runner SHALL treat a launch that discovers no test of the package
assembly as a failure rather than as a pass.

#### Scenario: A maintainer can run the EditMode tests headlessly

- **WHEN** a maintainer follows the documented command against a prepared Unity project
- **THEN** Unity runs the EditMode tests in batch mode
- **AND** the result is reported as test results rather than a host workflow outcome

#### Scenario: The real-host case is not replaced

- **WHEN** the play-mode compile-block behavior is validated
- **THEN** the real-host `wait-for-exec` continuation case still exists and still asserts the disclosure

#### Scenario: An undiscovered package assembly does not read as a pass

- **WHEN** the documented command runs against a host that does not declare the package testable
- **THEN** the runner reports that no test of the package assembly was discovered
- **AND** it does not report the harness as passing
