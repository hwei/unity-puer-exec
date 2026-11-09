# Spec Delta

## MODIFIED Requirements

### Requirement: Real-host validation preflights package compilation before launching an interactive Editor

Before a real-host run launches an interactive Editor, it SHALL perform a non-interactive
compile preflight of the validation host. The preflight SHALL fail the run with the parsed
compiler diagnostics when script compilation fails, so a package compile error is named
before the Editor's Safe Mode dialog can block an unattended run. The preflight SHALL also
fail the run when the log carries a deprecation diagnostic attributable to this package's own
source, so a build that compiles against an API its dependency has retired is named rather
than reported as passed. The preflight SHALL run once per suite invocation, not once per test
class.

#### Scenario: Package compile error fails the run before the interactive launch

- **WHEN** the repository-local package does not compile
- **AND** a real-host run starts
- **THEN** the preflight runs the host non-interactively and detects the compiler diagnostics
- **AND** the run fails with those diagnostics before any interactive Editor is launched

#### Scenario: Package deprecation diagnostic fails the run before the interactive launch

- **WHEN** the repository-local package compiles
- **AND** the batch log carries a deprecation diagnostic whose source location is inside this
  package
- **THEN** the preflight reports a failure that names the diagnostic, its code, and its source
  location
- **AND** the failure is distinguishable from a compile error
- **AND** the run fails before any interactive Editor is launched

#### Scenario: A host warning outside this package does not fail the run

- **WHEN** the batch log carries warnings whose source locations are outside this package
- **AND** the package itself produced no error and no deprecation diagnostic
- **THEN** the preflight succeeds
- **AND** those warnings are not counted as package diagnostics

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

## ADDED Requirements

### Requirement: Package-attributable diagnostics are resolved by source location and always reported

The preflight SHALL decide whether a diagnostic belongs to this package from the diagnostic's
own source location, and SHALL report every package-attributable warning in its result payload
whether or not that warning fails the run. The payload key carrying them SHALL be additive, so
a caller reading the existing status, exit code, and error diagnostics is unaffected.

#### Scenario: A non-fatal package warning is still visible in the payload

- **WHEN** the batch log carries a warning attributable to this package that is not a
  deprecation diagnostic
- **THEN** the preflight result carries that warning under the additive payload key
- **AND** the preflight still reports success

#### Scenario: Escalating every package warning is opt-in

- **WHEN** a caller asks the preflight to treat every package-attributable warning as a failure
- **THEN** a non-deprecation package warning fails the run
- **AND** without that request the same warning is reported and does not fail the run

#### Scenario: Attribution survives both host wirings

- **WHEN** the package reaches the host through a `file:` manifest entry, and when it reaches
  the host as an embedded copy under the host's own `Packages/` directory
- **THEN** a diagnostic in this package's source is attributed to this package in both wirings
- **AND** attribution does not depend on the diagnostic's path being absolute
