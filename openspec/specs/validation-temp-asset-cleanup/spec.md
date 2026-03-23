# validation-temp-asset-cleanup Specification

## Purpose
TBD - created by archiving change automate-validation-temp-asset-cleanup. Update Purpose after archive.
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

