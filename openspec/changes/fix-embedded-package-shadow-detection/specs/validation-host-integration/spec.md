## MODIFIED Requirements

### Requirement: Validation host preparation reports embedded package shadowing

Repository-owned validation-host preparation tooling SHALL report when the target Unity project contains an embedded package that declares the formal package name and is distinct from the repository-local package root being injected through `Packages/manifest.json`. Detection SHALL identify an embedded package the way Unity does — by the `name` declared in a candidate directory's `package.json` among the immediate children of `Packages/` — and SHALL NOT rely on the directory being named after the package, because Unity loads such a directory under any name. The report SHALL be machine-readable so real-host validation scripts and agents can treat the run as unsafe evidence for repository-local package changes unless the shadowing condition is resolved or intentionally accepted. When more than one embedded directory declares the formal package name, the report SHALL name all of them.

#### Scenario: Embedded package shadows local package injection
- **WHEN** a contributor prepares a validation host whose `Packages/manifest.json` is rewritten to the repository-local package path
- **AND** an immediate child of `Packages/` declares the formal package name in its `package.json` and is a distinct directory from the repository-local package root
- **THEN** the preparation result reports `embedded_package_shadowing = true`
- **AND** the result includes the embedded package path

#### Scenario: Renamed embedded directory is still reported
- **WHEN** an embedded package directory declaring the formal package name has been renamed to something other than the package name
- **THEN** the preparation result still reports `embedded_package_shadowing = true`
- **AND** the result names the renamed directory
- **AND** the result does not report the host as clean merely because no directory carries the package name

#### Scenario: No embedded package shadowing is present
- **WHEN** a contributor prepares a validation host in which no immediate child of `Packages/` declares the formal package name
- **THEN** the preparation result reports `embedded_package_shadowing = false`

#### Scenario: Embedded package path is the intended package root
- **WHEN** a contributor prepares a validation host whose embedded package path resolves to the same directory as the repository-local package root
- **THEN** the preparation result does not report shadowing

#### Scenario: Multiple shadowing directories are all reported
- **WHEN** more than one immediate child of `Packages/` declares the formal package name and is distinct from the repository-local package root
- **THEN** the preparation result reports shadowing
- **AND** the result names every such directory rather than only the first

#### Scenario: Unrelated or unreadable package directories are ignored
- **WHEN** an immediate child of `Packages/` has no `package.json`, has one that cannot be parsed, or declares a different package name
- **THEN** that directory does not contribute to the shadowing report
- **AND** the preparation run completes rather than failing on the unrelated directory

## ADDED Requirements

### Requirement: Real-host run instructions state how embedded shadowing is cleared

The repository's real-host run instructions SHALL state that renaming an embedded package directory does not stop Unity from loading it, because Unity identifies embedded packages by the `name` declared in `package.json`, and that clearing the shadow requires moving or removing the directory out of `Packages/`.

#### Scenario: Contributor resolves a reported shadowing condition
- **WHEN** a contributor consults the real-host run instructions after a shadowing report
- **THEN** the instructions state that renaming the directory is not sufficient
- **AND** the instructions state that the directory must be moved out of or removed from `Packages/`
