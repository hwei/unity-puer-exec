## ADDED Requirements

### Requirement: Version mismatch responses carry reconciliation guidance

The guidance matrix SHALL cover the `version_mismatch` status for every command that can return it. Because the resolution is an installation change rather than another CLI invocation, the response SHALL carry a `situation` explaining which two halves disagree and how they came to differ.

#### Scenario: Bridge mismatch explains the mixed installation

- **WHEN** a command returns `version_mismatch` from the bridge guard
- **THEN** the response includes a `situation` string stating that the CLI executable and the Unity Editor package ship as one release and that the two observed versions indicate a mixed installation

#### Scenario: Package-layout mismatch explains the stale binary

- **WHEN** a command returns `version_mismatch` from the package-layout guard
- **THEN** the response includes a `situation` string stating that the executable does not match the package tree it is installed in

#### Scenario: Unknown-version mismatch explains the unverifiable half

- **WHEN** a command returns `version_mismatch` because a counterpart reported no version
- **THEN** the response includes a `situation` string stating that the counterpart predates version reporting and therefore cannot be verified as compatible

### Requirement: Version mismatch guidance offers only verification follow-ups

The `next_steps` for `version_mismatch` SHALL be limited to actions that help the caller confirm the installation state. They SHALL NOT suggest re-running the failed command, and SHALL NOT reference any bypass mechanism, because neither would produce a trustworthy result.

#### Scenario: Guidance offers a version query

- **WHEN** a `version_mismatch` response includes `next_steps`
- **THEN** the candidates include `--version` for confirming the acting CLI build
- **AND** no candidate re-runs the failed command with the same mismatched pair

#### Scenario: Guidance does not offer a bypass

- **WHEN** a `version_mismatch` response includes `next_steps` or `situation`
- **THEN** neither references a flag, environment variable, or setting that would suppress the guard

### Requirement: Guidance suppression does not hide version mismatch detail

The `--suppress-guidance` flag SHALL continue to omit `next_steps` and `situation`, but SHALL NOT remove the structured version detail from a `version_mismatch` response, because that detail is the machine-readable result rather than advisory guidance.

#### Scenario: Suppressed guidance retains structured detail

- **WHEN** a caller invokes a command with `--suppress-guidance` and the command returns `version_mismatch`
- **THEN** the response omits `next_steps` and `situation`
- **AND** the response retains the guard identity, the CLI version, the observed counterpart version, and the observed location
