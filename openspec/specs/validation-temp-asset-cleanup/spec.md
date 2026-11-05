# validation-temp-asset-cleanup Specification

## Purpose
Ensure the validation harness removes the repository-owned temporary assets it created in the external Unity host after successful and failed runs alike, verifies and records the cleanup outcome, and leaves assets the live Editor still references in place.

## Requirements

### Requirement: Harness cleans repository-owned validation temp assets
The validation harness SHALL clean repository-owned temporary assets that were created in the external Unity validation host as part of repository validation workflows. The cleanup scope SHALL be limited to an explicit inventory of validation-temp roots or files that the repository declares safe to remove.

#### Scenario: Validation rerun creates temporary host assets
- **WHEN** a repository-owned validation rerun creates temporary C# files, scenes, or directories under a declared validation-temp root in the host Unity project
- **THEN** the harness MUST attempt cleanup after the run completes
- **AND** the cleanup target MUST be limited to the declared validation-temp inventory

### Requirement: Cleanup runs for both success and failure outcomes
The validation harness SHALL run cleanup regardless of whether the validation task passed or failed, so host-project residue does not accumulate across reruns.

#### Scenario: Validation task fails after creating temp assets
- **WHEN** a validation task ends in failure after creating files under a declared validation-temp root
- **THEN** the harness MUST still execute the cleanup step
- **AND** the cleanup attempt MUST be recorded in the durable validation evidence

### Requirement: Cleanup result is verified and recorded
The validation harness SHALL verify whether declared validation-temp assets remain after cleanup and SHALL persist the cleanup outcome in the durable validation record.

#### Scenario: Cleanup leaves residue
- **WHEN** the harness finishes a cleanup attempt and one or more declared validation-temp files or directories still exist
- **THEN** the durable validation record MUST report cleanup as partial or failed
- **AND** the record MUST identify the remaining residue at a concise file-or-directory level

### Requirement: Cleanup does not remove a temp asset the live Editor still references

The validation harness SHALL remove repository-owned validation temp assets only after the
live Editor's asset pipeline has released them, so removing a `.cs` or its `.meta` never
leaves the Editor opening a file that no longer exists.

#### Scenario: Cleanup runs while the shared Editor still holds a temp asset

- **WHEN** a cleanup targets a declared validation-temp root while the shared Editor still
  references a file under it
- **THEN** the harness removes the asset through the Editor's own asset pipeline, or waits
  until the Editor has released it
- **AND** it does not leave the Editor opening a deleted `.cs` or `.cs.meta`

#### Scenario: A skipped case leaves no trigger fixture

- **WHEN** the ScriptUpdater consent-dialog case is skipped after seeding its trigger fixture
- **THEN** the harness removes that fixture on the skip path
- **AND** a later cleanup does not encounter a file the Editor still references

### Requirement: The declared inventory covers every repository-owned asset the real-host suite creates

The declared validation-temp inventory SHALL include every repository-owned asset root that the
real-host validation suite creates in the host project, so a completed run leaves no residue the
harness is not permitted to remove. The agreement between the suite's creations and the inventory
SHALL be enforced by a repository test rather than left to memory, and that test SHALL fail when the
suite creates an asset root the inventory does not declare.

#### Scenario: A completed run leaves no undeclared residue

- **WHEN** a real-host validation run finishes, successfully or not
- **AND** the harness cleans the declared inventory
- **THEN** no repository-owned asset the suite created remains in the host project
- **AND** the host project's version-control status reports nothing the suite left behind

#### Scenario: The host-reset scene is declared and cleaned

- **WHEN** the real-host suite has written its host-reset baseline scene into the host project
- **AND** the harness runs its cleanup step
- **THEN** the scene, its directory, and their metadata are within the declared inventory
- **AND** the cleanup removes them under the same rules that govern the other declared roots

#### Scenario: A newly created suite asset that is not declared fails a repository test

- **WHEN** a contributor adds a repository-owned asset root that the real-host suite creates in the
  host project
- **AND** the declared inventory does not name it
- **THEN** a repository test in the default mocked suite fails and names the undeclared root
- **AND** the failure is visible without a Unity Editor or a validation host

#### Scenario: Declaring a root does not widen what the tool will touch on request

- **WHEN** a caller asks the cleanup tool to remove a path outside the declared inventory
- **THEN** the tool still refuses and names the inventory it is limited to
- **AND** adding a root to the inventory changes only what the harness itself cleans
