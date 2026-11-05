# Spec Delta

## ADDED Requirements

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
