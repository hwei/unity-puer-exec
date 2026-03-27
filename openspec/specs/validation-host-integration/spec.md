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

The validation host SHALL consume `com.txcombo.unity-puer-exec` through a local-only `manifest.json` injection. When the repository package root and host manifest share a filesystem anchor, the injected dependency SHALL use a reproducible relative `file:` path. When a Windows host manifest and repository package root are on different volumes, repository-owned helper tooling MUST emit a deterministic non-relative `file:` path instead of failing to rewrite the manifest.

#### Scenario: Host is wired to local package on the same filesystem anchor

- **WHEN** a contributor prepares the validation host for package testing and the manifest location can express the package root as a relative path
- **THEN** `Project/Packages/manifest.json` references the local package path using a reproducible relative `file:` dependency
- **AND** the repository documents or automates that wiring through a repository-owned helper workflow
- **AND** the manifest change is treated as local validation setup rather than normal host source control workflow

#### Scenario: Host manifest and package root are on different Windows volumes

- **WHEN** repository-owned helper tooling computes the local package dependency for a validation-host manifest on a different Windows volume from the repository package root
- **THEN** the helper emits a deterministic `file:` dependency value for the formal package
- **AND** the helper does not fail only because a relative path cannot be formed across volumes

### Requirement: Runtime validation stays distinct from wiring proof

The repository SHALL distinguish static host wiring proof from runtime validation proof. Manifest rewiring alone MAY establish local package injection readiness, but a repeatable runtime validation expectation MUST exist for proving that Unity imports and runs against the rewired package.

#### Scenario: Contributor claims host integration is complete

- **WHEN** local package host integration is treated as complete
- **THEN** the repository can point to both a wiring path and a runtime validation expectation
- **AND** manifest editing alone is not the only durable validation story

### Requirement: Real-host runtime validation covers critical CLI workflows

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path against both the repository-local package wiring path and the published OpenUPM install path when that path is under evaluation. For the published path, the durable record SHALL distinguish package acquisition blockers, import stabilization, and runtime workflow outcome instead of collapsing them into a single undifferentiated failure. For the hardened pending-artifact lifecycle, that workflow SHALL still prove the accepted `exec -> running -> wait-for-exec` recovery path against a real Unity host.

#### Scenario: Contributor validates the published OpenUPM install path against a real host

- **WHEN** a contributor evaluates the published `com.txcombo.unity-puer-exec` package through OpenUPM on the validation host
- **THEN** the repository-owned record states whether package acquisition succeeded, including whether registry access required proxy configuration
- **AND** the workflow waits until Unity import / domain reload activity is sufficiently stable before judging the representative `exec` path as failed
- **AND** the final record separates acquisition friction, editor stabilization friction, and post-install CLI outcome

#### Scenario: Contributor runs the critical real-host regression path

- **WHEN** a contributor runs the repository-owned real-host validation workflow against a prepared `UNITY_PROJECT_PATH`
- **THEN** the workflow exercises project-scoped readiness, project-scoped `exec`, and both high-level and low-level log-observation commands against the real Unity host
- **AND** the workflow uses the current exec observation checkpoint surface instead of relying on removed CLI flags
- **AND** the workflow reports failures in a form that distinguishes runtime host-validation regressions from ordinary mocked test failures

#### Scenario: Contributor validates accepted exec recovery after lifecycle hardening

- **WHEN** the real-host validation workflow triggers a project-scoped `exec` path that first returns an accepted non-terminal state and later continues through `wait-for-exec`
- **THEN** the workflow confirms the same `request_id` remains usable through completion
- **AND** the hardened pending-artifact lifecycle does not break the normal `exec -> running -> wait-for-exec` recovery path

### Requirement: Real-host observation validation proves checkpoint compatibility

The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec` remains compatible with the actual log source consumed by the CLI observation commands, including the case where a first observation attempt happens during import churn and the same request later becomes recoverable.

#### Scenario: Contributor validates observation from the returned checkpoint

- **WHEN** the real-host validation workflow starts an execution that emits a correlation-aware result marker and then observes from the checkpoint returned in the exec response
- **THEN** `wait-for-result-marker` succeeds from that checkpoint against the real host
- **AND** `wait-for-log-pattern` with structured extraction can observe the same marker from a compatible checkpoint without falling back to a full-log scan

#### Scenario: Contributor observes a package-local exec request through import churn

- **WHEN** a contributor starts a package-local `exec` request while the editor is still stabilizing after package installation and the initial transport response is ambiguous or delayed
- **THEN** the durable validation record treats the request as recoverable until `wait-for-exec`, `wait-for-result-marker`, or equivalent follow-up proves otherwise
- **AND** a later successful result for the same request is recorded as evidence that the earlier transport noise was not by itself a workflow failure

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

### Requirement: Real-host validation remains outside the default unit-test workflow
The repository SHALL keep real-host validation as a separate workflow surface from the default automated unit-test action. The default GitHub Actions unit-test workflow MUST NOT treat a skipped real-host test file as the mechanism for separating Unity-dependent validation from mocked/unit coverage.

#### Scenario: Maintainer reviews default CI coverage
- **WHEN** a maintainer inspects the repository's default automated unit-test workflow
- **THEN** the workflow does not include `tests/test_real_host_integration.py` in its selected test set
- **AND** the real-host validation path remains separately documented for machines that provide Unity Editor and `UNITY_PROJECT_PATH`

### Requirement: Real-host sequential validation establishes a clean readiness boundary

The repository-owned real-host validation workflow SHALL establish a repeatable boundary between one project-scoped test case ending and the next readiness attempt beginning. A previous case leaving behind a stale session artifact, a fresh `UnityLockfile`, or an incomplete stop result MUST NOT by itself convert the next case into an unexplained readiness stall.

#### Scenario: Contributor runs sequential real-host cases in one suite invocation

- **WHEN** one real-host validation case tears down Unity for the target `UNITY_PROJECT_PATH` and the next case immediately starts another project-scoped readiness attempt
- **THEN** the repository-owned workflow either confirms the previous stop completed, waits until the target is genuinely recoverable, or launches a new editor cleanly
- **AND** a failure reports enough machine-usable state to distinguish incomplete stop or stale recovery evidence from a true runtime readiness regression

