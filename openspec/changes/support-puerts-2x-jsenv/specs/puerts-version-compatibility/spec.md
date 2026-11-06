# Spec Delta

## Purpose

Define which `com.tencent.puerts.core` major versions the package supports, how the active major is
determined on a given host, and what a host on each supported version observes from the package.

## ADDED Requirements

### Requirement: The package declares the lowest PuerTS version it supports

The published package SHALL declare `com.tencent.puerts.core` as a dependency at the lowest version it
supports, so that any host at or above that version resolves the package without operator intervention.

#### Scenario: A host at the declared floor installs the package

- **WHEN** a host project has `com.tencent.puerts.core` 2.2.2 installed
- **AND** the host manifest adds `com.txcombo.unity-puer-exec`
- **THEN** package resolution succeeds
- **AND** the host reports no unmet dependency for `com.tencent.puerts.core`

#### Scenario: A host above the declared floor installs the package unchanged

- **WHEN** a host project has `com.tencent.puerts.core` 3.0.0 installed
- **AND** the host manifest adds the same published package
- **THEN** package resolution succeeds with no change to the package or the host

### Requirement: The Editor assembly compiles on every supported PuerTS major

On a host whose installed `com.tencent.puerts.core` is any supported major version, the package's Editor
assembly SHALL compile without an error attributable to the package, and the control endpoint SHALL become
available to the CLI.

#### Scenario: A 2.x host compiles the package and serves requests

- **WHEN** the Editor opens a host project whose `com.tencent.puerts.core` is 2.2.2
- **AND** the package is installed and the Editor is launched with the control argument
- **THEN** the Editor reports no compile error naming a PuerTS type the package references
- **AND** the endpoint publication the CLI discovers is written
- **AND** an `exec` request against that endpoint reaches a terminal status

#### Scenario: A 3.x host keeps compiling the package

- **WHEN** the Editor opens a host project whose `com.tencent.puerts.core` is 3.0.0
- **AND** the same package source is installed
- **THEN** the Editor reports no compile error attributable to the package
- **AND** an `exec` request reaches a terminal status

### Requirement: The active PuerTS major is resolved from the host's installed version

The package SHALL determine the PuerTS major version from the version of `com.tencent.puerts.core` the host
actually has installed. It SHALL NOT require an operator to edit package source, set a scripting define, or
choose a package variant by hand.

#### Scenario: One published package serves both majors

- **WHEN** the same published package version is installed into a 2.x host and into a 3.x host
- **THEN** each host selects the environment-construction path belonging to its own installed PuerTS major
- **AND** neither host requires a package edit

#### Scenario: A host upgrades its PuerTS major

- **WHEN** a host replaces `com.tencent.puerts.core` 2.2.2 with 3.0.0
- **AND** the installed package is left untouched
- **THEN** the package's Editor assembly recompiles against the new major
- **AND** no operator change to the package is needed

### Requirement: CLI-observable behavior is identical across supported majors

Everything the CLI can observe — endpoint names, request and response payloads, `exec` semantics, module-cache
reset, and disposal and recreation of the JavaScript environment — SHALL be the same on every supported PuerTS
major. A host's PuerTS major SHALL NOT appear in, or change the shape of, any response payload.

#### Scenario: exec on a 2.x host returns the same payload shape as on 3.x

- **WHEN** the same `exec` invocation is run against a 2.x host and against a 3.x host
- **THEN** both return the same operation, phase, and status vocabulary
- **AND** neither payload carries a PuerTS version field

#### Scenario: Module-cache reset works on a 2.x host

- **WHEN** `exec --reset-jsenv-before-exec` runs against a 2.x host
- **THEN** the JavaScript environment is disposed and recreated
- **AND** a module imported by an earlier exec is loaded again rather than served from cache

### Requirement: A host below the declared floor is rejected before compile

A host whose `com.tencent.puerts.core` is older than the declared minimum SHALL be turned away by package
resolution rather than by a compile failure in package code. The package SHALL NOT carry source paths for
majors it does not support.

#### Scenario: A pre-2.2.2 host cannot resolve the package

- **WHEN** a host project has a `com.tencent.puerts.core` older than the declared minimum
- **AND** the host manifest adds the package
- **THEN** package resolution reports the unmet dependency
- **AND** the failure is reported as a dependency problem, not as a C# compile error in the package
