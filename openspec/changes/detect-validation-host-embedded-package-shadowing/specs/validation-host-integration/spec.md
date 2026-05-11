## ADDED Requirements

### Requirement: Validation host preparation reports embedded package shadowing

Repository-owned validation-host preparation tooling SHALL report when the target Unity project contains an embedded `Packages/com.txcombo.unity-puer-exec` directory that is distinct from the repository-local package root being injected through `Packages/manifest.json`. The report SHALL be machine-readable so real-host validation scripts and agents can treat the run as unsafe evidence for repository-local package changes unless the shadowing condition is resolved or intentionally accepted.

#### Scenario: Embedded package shadows local package injection
- **WHEN** a contributor prepares a validation host whose `Packages/manifest.json` is rewritten to the repository-local package path
- **AND** `<project>/Packages/com.txcombo.unity-puer-exec` exists as a distinct embedded package directory
- **THEN** the preparation result reports `embedded_package_shadowing = true`
- **AND** the result includes the embedded package path

#### Scenario: No embedded package shadowing is present
- **WHEN** a contributor prepares a validation host whose `Packages/com.txcombo.unity-puer-exec` directory is absent
- **THEN** the preparation result reports `embedded_package_shadowing = false`

#### Scenario: Embedded package path is the intended package root
- **WHEN** a contributor prepares a validation host whose embedded package path resolves to the same directory as the repository-local package root
- **THEN** the preparation result does not report shadowing
