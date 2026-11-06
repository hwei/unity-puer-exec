# Spec Delta

## MODIFIED Requirements

### Requirement: Help documents a cross-environment coordination pattern

Because the boundary alone tells a caller only what does not work, help SHALL describe the generic pattern that does: place or read state through shared C#/Unity objects that both sides can observe, and confirm the outcome through log-based observation. The pattern SHALL be described without depending on any particular UI framework or application architecture. Where the bridge exposes the host application's own JavaScript environments, help SHALL name that route and SHALL state that it is outside this CLI's contract, rather than asserting that no such route exists.

#### Scenario: Agent needs the running application to perform work

- **WHEN** an agent reads help while looking for a way to invoke the host application's own JavaScript functions
- **THEN** help describes shared-object coordination plus log observation as the supported approach
- **AND** help names the bridge-reachable host-environment enumeration as an escape hatch that is outside this CLI's contract
- **AND** help does not assert that no mechanism for reaching the host application's JavaScript runtime exists

#### Scenario: Agent reads the coordination pattern without a specific UI framework in mind

- **WHEN** an agent reads the cross-environment coordination guidance
- **THEN** the pattern is described in terms of shared C#/Unity state and log observation
- **AND** it does not depend on any particular UI framework or application architecture

## ADDED Requirements

### Requirement: Help bounds the host JavaScript environment escape hatch

Help SHALL state that reaching the host application's JavaScript environments goes through
PuerTS internals whose entry point differs by PuerTS major, and SHALL NOT present that route as
a guaranteed interface of this CLI. Help SHALL keep stating that an `exec` script's own
environment is separate from the host application's runtime, so the escape hatch reads as an
exception to a real boundary rather than as the normal path.

#### Scenario: Agent considers driving the host application's JavaScript directly

- **WHEN** an agent reads help about reaching the host application's JavaScript runtime
- **THEN** help names the PuerTS-major-specific entry point for enumerating host environments
- **AND** help states that this is PuerTS-internal and outside the CLI's contract
- **AND** help still states that the `exec` script environment is separate from the host application's runtime

#### Scenario: PuerTS major changes the entry point name

- **WHEN** help describes enumerating the host application's JavaScript environments
- **THEN** help does not present a single field name as valid across PuerTS majors
- **AND** a reader can tell that the name depends on the installed PuerTS major

#### Scenario: Help text is pinned against regression to the absolute denial

- **WHEN** the repository's help-surface tests run
- **THEN** a test asserts that exec help no longer claims there is no supported way to reach the host application's JavaScript runtime
- **AND** the same test asserts the escape hatch is presented as outside the CLI contract
