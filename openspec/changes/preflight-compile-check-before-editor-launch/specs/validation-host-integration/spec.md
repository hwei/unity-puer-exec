## ADDED Requirements

### Requirement: Real-host validation preflights package compilation before launching an interactive Editor

Before a real-host run launches an interactive Editor, it SHALL perform a non-interactive
compile preflight of the validation host. The preflight SHALL fail the run with the parsed
compiler diagnostics when script compilation fails, so a package compile error is named
before the Editor's Safe Mode dialog can block an unattended run. The preflight SHALL run
once per suite invocation, not once per test class.

#### Scenario: Package compile error fails the run before the interactive launch

- **WHEN** the repository-local package does not compile
- **AND** a real-host run starts
- **THEN** the preflight runs the host non-interactively and detects the compiler diagnostics
- **AND** the run fails with those diagnostics before any interactive Editor is launched

#### Scenario: Compilable package proceeds to the interactive launch

- **WHEN** the repository-local package compiles
- **THEN** the preflight succeeds
- **AND** the real-host run proceeds to launch the interactive Editor as before

#### Scenario: Preflight does not multiply launch cost

- **WHEN** a real-host invocation runs several test classes
- **THEN** the compile preflight runs once for the invocation
- **AND** each class still reuses one shared interactive host

#### Scenario: Preflight skips with the opt-in gate

- **WHEN** the real-host tests are not enabled, or the validation host project or a Unity
  executable is unavailable
- **THEN** the preflight is skipped
- **AND** it does not turn the existing skip into a failure
