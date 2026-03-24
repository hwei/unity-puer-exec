## ADDED Requirements

### Requirement: Exec file-entry guidance is explicit at help time and failure time
The CLI SHALL make the required default-export script entry shape explicit in `exec` help and in the `missing_default_export` failure path.

#### Scenario: Contributor authors a file-based exec script
- **WHEN** a contributor prepares a script for `exec --file`
- **THEN** the published help states the required `export default function (ctx) { ... }` shape clearly enough to serve as a first-pass template
- **AND** if the contributor still misses that contract, the failure response points back to the expected minimal shape
- **AND** Prompt B validation can compare whether first-pass script authoring still fails with `missing_default_export`
