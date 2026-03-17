## ADDED Requirements

### Requirement: Unity project path resolution is deterministic

The repository SHALL resolve Unity project targeting in this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. `UNITY_PROJECT_PATH` loaded from repository-local `.env`
4. current working directory

#### Scenario: Explicit project path is supplied

- **WHEN** a caller provides `--project-path`
- **THEN** the repository uses that path instead of any environment or `.env` fallback

#### Scenario: Process environment overrides repository-local defaults

- **WHEN** `--project-path` is absent and `UNITY_PROJECT_PATH` exists in the process environment
- **THEN** the repository uses the process environment value
- **AND** the repository does not prefer the repository-local `.env` value over it

### Requirement: Validation host remains separate from product source

The validation host MUST remain a harness for exercising `unity-puer-exec`, not the repository that owns the product's long-lived source of truth. Product package code, product CLI code, and product-facing documentation SHALL be owned by this repository.

#### Scenario: Contributor prepares host validation

- **WHEN** validation work is performed against the Unity host project
- **THEN** the host starts from a clean baseline that does not already carry the formal package as committed host source
- **AND** host-local test injection changes remain uncommitted by default unless the host has its own independent need for them

### Requirement: Local package injection is the default host wiring model

Validation against the formal Unity package SHALL prefer a local-only `manifest.json` injection workflow that points the validation host at `packages/com.txcombo.unity-puer-exec/` through a reproducible relative path.

#### Scenario: Host is wired to local package source

- **WHEN** the validation host is prepared for local package testing
- **THEN** `Project/Packages/manifest.json` references `com.txcombo.unity-puer-exec` via a local file path into this repository
- **AND** the helper workflow is discoverable from the repository
- **AND** that manifest edit is treated as local validation wiring instead of normal committed host workflow

### Requirement: Validation expectations distinguish wiring proof from runtime proof

The repository SHALL distinguish static host-wiring preparation from runtime validation. Static manifest rewiring MAY prove package injection readiness by itself, but a separate validation path MUST exist for proving that Unity actually imports and runs against the rewired local package.

#### Scenario: Contributor claims host integration is validated

- **WHEN** a contributor reports the local package integration as complete
- **THEN** the repository can show both the host wiring model and a repeatable runtime validation expectation
- **AND** the repository does not treat manifest rewriting alone as the only long-term validation requirement

