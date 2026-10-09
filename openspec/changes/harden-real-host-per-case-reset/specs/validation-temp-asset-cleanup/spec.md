# Spec Delta

## ADDED Requirements

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
