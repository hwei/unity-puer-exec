# Spec Delta

## MODIFIED Requirements

### Requirement: package.json includes required OpenUPM metadata

The package.json SHALL include `license`, `repository`, `author`, and `dependencies` fields in addition to existing fields. The `author.name` SHALL be `Will Huang`. The `license` SHALL be `MIT`. The `dependencies` SHALL declare `com.tencent.puerts.core` at minimum version `2.2.2`, the lowest version the package supports.

#### Scenario: OpenUPM validates package metadata

- **WHEN** OpenUPM ingests the package from the `upm` branch
- **THEN** the package.json contains a valid `license` field set to `MIT`
- **AND** the package.json contains a `repository` field pointing to the GitHub repo
- **AND** the package.json contains `author.name` set to `Will Huang`
- **AND** the package.json contains `dependencies` with `com.tencent.puerts.core` at `2.2.2`

#### Scenario: A 2.x host resolves the published package

- **WHEN** a consumer project with `com.tencent.puerts.core` 2.2.2 installs the package from OpenUPM
- **THEN** the declared dependency is satisfied
- **AND** OpenUPM reports no unmet dependency for the consumer
