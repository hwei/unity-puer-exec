# Spec Delta

## Purpose

Record that a validation host which loads a separate copy of the package must carry the release candidate version before real-host validation is evidence, and that the release helper diagnoses or aligns that identity.

## ADDED Requirements

### Requirement: Run instructions state the release-time host package identity rule

The repository's real-host run instructions SHALL state that a host loading an embedded copy of the package must declare the release candidate version before a real-host run counts as evidence for the release, what happens when it does not, and how the release helper reports or aligns it.

#### Scenario: Contributor reads the prerequisites before a release

- **WHEN** a contributor consults the real-host run instructions before preparing a release
- **THEN** the instructions state that a host loading an embedded package copy must declare the version being released
- **AND** the instructions state that the release helper refuses real-host validation when the loaded version differs, and names the loaded path and both versions
- **AND** the instructions state that the helper aligns the version only when explicitly asked and only when the copy's content matches the repository package
- **AND** the instructions state that a running Editor must be restarted for the host to report the aligned version

#### Scenario: Host is wired only through the file dependency

- **WHEN** a contributor's host has no embedded package copy and loads the package through the manifest `file:` dependency
- **THEN** the instructions state that no host version action is required, because the loaded package is the repository package
