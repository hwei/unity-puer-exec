# Validation Host Integration

## Purpose

Define the stable contract between this repository and the external Unity validation host, including project-path resolution, host boundaries, local package wiring, and validation expectations.

## Requirements

### Requirement: Unity project path resolution is deterministic

Unity project path resolution SHALL follow this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. `UNITY_PROJECT_PATH` loaded from repository-local `.env`
4. current working directory

#### Scenario: Explicit project path wins

- **WHEN** a caller passes `--project-path`
- **THEN** the repository uses that value instead of any environment-derived fallback

#### Scenario: Process environment overrides `.env`

- **WHEN** `--project-path` is absent and `UNITY_PROJECT_PATH` is present in the process environment
- **THEN** the repository uses the process-environment value
- **AND** the repository does not prefer the repository-local `.env` value over it

### Requirement: Product and validation host remain separate

This repository SHALL remain the source of truth for the formal Unity package, the formal CLI, and product-facing documentation. The validation host SHALL exist only to exercise and verify the product against a real Unity project.

#### Scenario: Contributor prepares validation work

- **WHEN** host validation begins
- **THEN** the validation host starts from a clean baseline that does not carry the formal package as committed host source
- **AND** host-local injection edits remain uncommitted by default unless the host has its own independent need

### Requirement: Local package injection is the normal host wiring path

The validation host SHALL consume `com.txcombo.unity-puer-exec` through a local-only `manifest.json` injection that points at `packages/com.txcombo.unity-puer-exec/` using a reproducible relative file path.

#### Scenario: Host is wired to local package

- **WHEN** a contributor prepares the validation host for package testing
- **THEN** `Project/Packages/manifest.json` references the local package path
- **AND** the repository documents or automates that wiring through a repository-owned helper workflow
- **AND** the manifest change is treated as local validation setup rather than normal host source control workflow

### Requirement: Runtime validation stays distinct from wiring proof

The repository SHALL distinguish static host wiring proof from runtime validation proof. Manifest rewiring alone MAY establish local package injection readiness, but a repeatable runtime validation expectation MUST exist for proving that Unity imports and runs against the rewired package.

#### Scenario: Contributor claims host integration is complete

- **WHEN** local package host integration is treated as complete
- **THEN** the repository can point to both a wiring path and a runtime validation expectation
- **AND** manifest editing alone is not the only durable validation story
