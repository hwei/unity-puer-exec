# Spec Delta

## ADDED Requirements

### Requirement: Validation host preparation can clear and restore an embedded shadow

Validation-host preparation tooling SHALL offer a paired operation that clears an embedded package
shadow by moving every shadowing directory out of `Packages/` into a host-local backup, and restores
it by the exact inverse move. Neither direction SHALL delete anything, and neither SHALL perform a
version-control operation on the host project. Both SHALL report machine-readably which action they
took, the backup path involved, and the resulting shadowing value.

#### Scenario: Clearing moves every shadowing directory out of Packages

- **WHEN** a contributor asks preparation to clear an embedded shadow
- **AND** one or more immediate children of `Packages/` declare the formal package name and are
  distinct from the repository-local package root
- **THEN** the tool moves each such directory into a host-local backup outside `Packages/`
- **AND** it reports the cleared status, the backup path, and every directory it moved
- **AND** a following preparation run reports `embedded_package_shadowing = false`

#### Scenario: Restoring is the exact inverse

- **WHEN** a contributor asks preparation to restore a previously cleared embedded package
- **AND** the backup holds the directories the clear moved
- **THEN** the tool moves them back to their original `Packages/` paths
- **AND** the host project's version-control status matches what it was before the clear
- **AND** nothing is deleted in either direction

#### Scenario: Both operations are idempotent

- **WHEN** a contributor asks to clear a host that has no embedded shadow
- **OR** asks to restore a host whose embedded package is already in place
- **THEN** the tool reports an unchanged status rather than failing
- **AND** it writes nothing

#### Scenario: A restore refuses rather than merging into an occupied target

- **WHEN** a contributor asks to restore an embedded package
- **AND** the corresponding `Packages/` child already exists
- **THEN** the tool refuses and names the occupied path
- **AND** it neither merges the two copies nor overwrites either one

#### Scenario: A clear refuses when its backup path is already occupied

- **WHEN** a contributor asks to clear an embedded shadow
- **AND** the backup path for that directory already holds content
- **THEN** the tool refuses and names the occupied backup path
- **AND** it leaves the embedded package where it is

### Requirement: Shadow switching refuses on a host that is not free

The clear and restore operations SHALL refuse when the target host project is not free, decided from
project-local state alone, because moving a package under a live Editor leaves its asset database
describing a package that is no longer there. The tool SHALL report the refusal and the evidence it
used, and SHALL NOT stop an Editor process.

#### Scenario: A live Editor serving the host blocks the operation

- **WHEN** a contributor asks to clear or restore an embedded shadow
- **AND** the host project's own lockfile is held or its Editor has published a control endpoint
- **THEN** the tool refuses and names the project-local evidence it used
- **AND** it moves nothing
- **AND** it does not terminate any Editor process

#### Scenario: A free host proceeds

- **WHEN** the host project's lockfile is not held and no Editor has published an endpoint for it
- **THEN** the requested clear or restore proceeds

### Requirement: Shadow switching is previewable without writing

The clear and restore operations SHALL honour the existing preview mode, reporting what they would
move and where without writing anything, so an operator can inspect the effect on a host project
before allowing a move of files that project tracks.

#### Scenario: Preview reports the intended moves

- **WHEN** a contributor asks to clear or restore an embedded shadow in preview mode
- **THEN** the tool reports the directories it would move and the backup path it would use
- **AND** it writes nothing and reports the preview status rather than a performed one

## MODIFIED Requirements

### Requirement: Real-host run instructions state how embedded shadowing is cleared

The repository's real-host run instructions SHALL state that renaming an embedded package directory does not stop Unity from loading it, because Unity identifies embedded packages by the `name` declared in `package.json`, and that clearing the shadow requires moving or removing the directory out of `Packages/`. The instructions SHALL name the repository-owned operation that performs that move and the paired operation that reverses it, so a contributor does not have to reconstruct the sequence by hand, and SHALL state that both refuse while the host project is not free.

#### Scenario: Contributor resolves a reported shadowing condition
- **WHEN** a contributor consults the real-host run instructions after a shadowing report
- **THEN** the instructions state that renaming the directory is not sufficient
- **AND** the instructions state that the directory must be moved out of or removed from `Packages/`

#### Scenario: Contributor uses the repository-owned operation instead of a manual move
- **WHEN** a contributor needs the validation host to load repository-local package code
- **THEN** the instructions name the operation that clears the shadow and the one that restores it
- **AND** they state that the pair leaves the host project's version-control status as it was found
- **AND** they state that both refuse while an Editor is serving the host project
