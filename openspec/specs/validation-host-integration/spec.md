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

### Requirement: Real-host runtime validation covers critical CLI workflows

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path, not only manifest rewiring or mocked Python contracts. For the hardened pending-artifact lifecycle, that workflow SHALL still prove the accepted `exec -> running -> wait-for-exec` recovery path against a real Unity host.

#### Scenario: Contributor runs the critical real-host regression path

- **WHEN** a contributor runs the repository-owned real-host validation workflow against a prepared `UNITY_PROJECT_PATH`
- **THEN** the workflow exercises project-scoped readiness, `exec --include-log-offset`, and both high-level and low-level log-observation commands against the real Unity host
- **AND** the workflow reports failures in a form that distinguishes runtime host-validation regressions from ordinary mocked test failures

#### Scenario: Contributor validates accepted exec recovery after lifecycle hardening

- **WHEN** the real-host validation workflow triggers a project-scoped `exec` path that first returns an accepted non-terminal state and later continues through `wait-for-exec`
- **THEN** the workflow confirms the same `request_id` remains usable through completion
- **AND** the hardened pending-artifact lifecycle does not break the normal `exec -> running -> wait-for-exec` recovery path

### Requirement: Real-host observation validation proves checkpoint compatibility
The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec --include-log-offset` remains compatible with the actual log source consumed by the CLI observation commands.

#### Scenario: Contributor validates observation from the returned checkpoint
- **WHEN** the real-host validation workflow starts an execution that emits a correlation-aware result marker and then observes from the returned `log_offset`
- **THEN** `wait-for-result-marker` succeeds from that checkpoint against the real host
- **AND** `wait-for-log-pattern` with structured extraction can observe the same marker from a compatible checkpoint without falling back to a full-log scan

### Requirement: Real-host validation covers repeated project-scoped startup attempts

The repository SHALL maintain a repeatable real-host validation expectation proving that project-scoped CLI startup remains stable when the target Unity project is already open or already recovering.

#### Scenario: Contributor validates readiness against an already-open target project

- **WHEN** a contributor first ensures the validation host project is already open in Unity Editor and then runs the repository-owned readiness workflow again for the same `UNITY_PROJECT_PATH`
- **THEN** the CLI reports a machine-usable recovery or launch-conflict result
- **AND** the workflow does not rely on a Unity-native duplicate-open dialog as the primary observable outcome

#### Scenario: Contributor validates project-scoped exec after the editor is already open

- **WHEN** a contributor runs the repository-owned real-host `exec --project-path ...` workflow after the validation host project is already open or recovering
- **THEN** the CLI reuses or safely recovers the existing project-scoped runtime before execution
- **AND** the workflow does not trigger a blind competing launch for the same project

### Requirement: Real-host validation can reproduce and record modal dialog blockers
The repository SHALL maintain a repeatable real-host validation expectation for at least one Unity-native modal dialog blocker scenario so contributors can distinguish CLI contract regressions from editor-side blocking behavior.

#### Scenario: Contributor validates a save-scene modal blocker path
- **WHEN** a contributor runs the repository-owned real-host validation workflow for a scenario that triggers a Unity-native save-scene modal dialog
- **THEN** the workflow records whether the CLI exposed a machine-usable blocker outcome or blocker diagnostics
- **AND** the workflow does not treat a manual operator click-through as equivalent to normal unattended success

#### Scenario: Contributor validates the untitled-scene save dialog path
- **WHEN** the real-host validation workflow triggers a new untitled scene save request that opens the `Save Scene` file-save dialog
- **THEN** follow-up CLI observation can report `status = "modal_blocked"`
- **AND** the observed blocker payload records `blocker.type = "save_scene_dialog"`

### Requirement: Real-host validation can resolve supported modal blockers

The repository SHALL maintain real-host validation coverage for resolving the supported Unity save-scene modal blockers through the CLI.

#### Scenario: Contributor resolves the modified-scenes prompt through the CLI

- **WHEN** the real-host validation workflow triggers the `Scene(s) Have Been Modified` dialog and then invokes `resolve-blocker --action cancel`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_modified_scenes_prompt"`
- **AND** follow-up observation can continue through `wait-for-exec` on the original request

#### Scenario: Contributor resolves the save-scene dialog through the CLI

- **WHEN** the real-host validation workflow triggers the `Save Scene` dialog and then invokes `resolve-blocker --action cancel`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_scene_dialog"`
- **AND** the workflow confirms the dialog is no longer present before treating the resolution as successful

