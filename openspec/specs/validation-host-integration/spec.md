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

The repository SHALL provide a repeatable runtime validation workflow for the external Unity host that exercises the critical project-scoped CLI integration path against both the repository-local package wiring path and the published OpenUPM install path when that path is under evaluation. For the published path, the durable record SHALL distinguish package acquisition blockers, import stabilization, and runtime workflow outcome instead of collapsing them into a single undifferentiated failure.

#### Scenario: Contributor validates the published OpenUPM install path against a real host

- **WHEN** a contributor evaluates the published `com.txcombo.unity-puer-exec` package through OpenUPM on the validation host
- **THEN** the repository-owned record states whether package acquisition succeeded, including whether registry access required proxy configuration
- **AND** the workflow waits until Unity import / domain reload activity is sufficiently stable before judging the representative `exec` path as failed
- **AND** the final record separates acquisition friction, editor stabilization friction, and post-install CLI outcome

### Requirement: Real-host observation validation proves checkpoint compatibility

The repository SHALL maintain a repeatable real-host validation expectation proving that the observation checkpoint returned by `exec` remains compatible with the actual log source consumed by the CLI observation commands, including the case where a first observation attempt happens during import churn and the same request later becomes recoverable.

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

### Requirement: Validation host preparation reports embedded package shadowing

Repository-owned validation-host preparation tooling SHALL report when the target Unity project contains an embedded package that declares the formal package name and is distinct from the repository-local package root being injected through `Packages/manifest.json`. Detection SHALL identify an embedded package the way Unity does — by the `name` declared in a candidate directory's `package.json` among the immediate children of `Packages/` — and SHALL NOT rely on the directory being named after the package, because Unity loads such a directory under any name. The report SHALL be machine-readable so real-host validation scripts and agents can treat the run as unsafe evidence for repository-local package changes unless the shadowing condition is resolved or intentionally accepted. When more than one embedded directory declares the formal package name, the report SHALL name all of them.

#### Scenario: Embedded package shadows local package injection
- **WHEN** a contributor prepares a validation host whose `Packages/manifest.json` is rewritten to the repository-local package path
- **AND** an immediate child of `Packages/` declares the formal package name in its `package.json` and is a distinct directory from the repository-local package root
- **THEN** the preparation result reports `embedded_package_shadowing = true`
- **AND** the result includes the embedded package path

#### Scenario: Renamed embedded directory is still reported
- **WHEN** an embedded package directory declaring the formal package name has been renamed to something other than the package name
- **THEN** the preparation result still reports `embedded_package_shadowing = true`
- **AND** the result names the renamed directory
- **AND** the result does not report the host as clean merely because no directory carries the package name

#### Scenario: No embedded package shadowing is present
- **WHEN** a contributor prepares a validation host in which no immediate child of `Packages/` declares the formal package name
- **THEN** the preparation result reports `embedded_package_shadowing = false`

#### Scenario: Embedded package path is the intended package root
- **WHEN** a contributor prepares a validation host whose embedded package path resolves to the same directory as the repository-local package root
- **THEN** the preparation result does not report shadowing

#### Scenario: Multiple shadowing directories are all reported
- **WHEN** more than one immediate child of `Packages/` declares the formal package name and is distinct from the repository-local package root
- **THEN** the preparation result reports shadowing
- **AND** the result names every such directory rather than only the first

#### Scenario: Unrelated or unreadable package directories are ignored
- **WHEN** an immediate child of `Packages/` has no `package.json`, has one that cannot be parsed, or declares a different package name
- **THEN** that directory does not contribute to the shadowing report
- **AND** the preparation run completes rather than failing on the unrelated directory

### Requirement: Real-host validation covers control-port binding behavior

The repository SHALL maintain repeatable real-host validation expectations that prove the Unity control-port binding contract, covering the uniform activation rule in batch mode (both with and without activation requested) and occupied-preferred-port rollover. These expectations SHALL run only under the existing opt-in real-host gate and SHALL skip cleanly when Unity, the host project, or the required process state is unavailable, so the default mocked/unit workflow is unaffected.

#### Scenario: Contributor validates that a batch-mode process without activation does not start the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched without activation requested
- **THEN** the validation asserts the batch-mode process log records that the control service was not activated for that process
- **AND** the validation asserts the batch-mode process log records no successful control-port bind and no whole-range bind failure

#### Scenario: Contributor validates that a batch-mode process with activation starts the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched with activation requested
- **THEN** the validation asserts the batch-mode process log records a successful control-port bind
- **AND** the validation asserts the batch-mode process log does not record that the control service was not activated

#### Scenario: Contributor validates rollover when the preferred control port is occupied

- **WHEN** a contributor runs the real-host validation with the preferred control port already occupied at the time an interactive control service starts
- **THEN** the validation asserts the interactive control service becomes ready on a later port in the bounded range rather than failing the whole scan
- **AND** the validation asserts the ready health identity reports the later selected port and its base URL

#### Scenario: Prerequisites for binding validation are absent

- **WHEN** the real-host gate is disabled, or Unity / the host project / the required process state is unavailable
- **THEN** the binding-behavior validation skips with a machine-usable reason
- **AND** it does not report a failure that would be indistinguishable from a real binding regression

### Requirement: Real-host run instructions state how embedded shadowing is cleared

The repository's real-host run instructions SHALL state that renaming an embedded package directory does not stop Unity from loading it, because Unity identifies embedded packages by the `name` declared in `package.json`, and that clearing the shadow requires moving or removing the directory out of `Packages/`.

#### Scenario: Contributor resolves a reported shadowing condition
- **WHEN** a contributor consults the real-host run instructions after a shadowing report
- **THEN** the instructions state that renaming the directory is not sufficient
- **AND** the instructions state that the directory must be moved out of or removed from `Packages/`

### Requirement: Real-host validation observes a log no unrelated Editor can share

Real-host validation SHALL observe the validation host through a log source private to the host project, so a Unity Editor open on an unrelated project cannot share, rotate, or truncate the file the suite reads. A development machine running several Unity projects at once SHALL remain a supported environment for real-host validation.

The suite SHALL establish its clean starting boundary from project-local state — the host project's Unity lockfile and published endpoint — so that a boundary check cannot report the host as stopped while an Editor is still serving it. A case SHALL fail rather than proceed if it would observe a host the suite did not bring up.

#### Scenario: Concurrent unrelated Editor does not invalidate observation

- **WHEN** real-host validation runs while an unrelated Unity Editor is open on a different project
- **THEN** the suite observes the validation host through a host-private log
- **AND** log-based assertions reflect output the validation host actually produced

#### Scenario: Host-private log is established without per-command flags

- **WHEN** the suite brings up the validation host
- **THEN** the host-private log is established at launch
- **AND** individual cases do not each have to supply a log-path flag to observe it

#### Scenario: The boundary cannot pass while the host is still serving

- **WHEN** the suite establishes its starting boundary and an Editor is still serving the host project
- **THEN** the boundary does not report the host as stopped
- **AND** no case proceeds against that Editor

#### Scenario: An unrelated Editor does not block the boundary

- **WHEN** the suite establishes its starting boundary while unrelated Unity Editors are running for other projects
- **THEN** those processes do not prevent the boundary from being established

### Requirement: Real-host run instructions state the concurrent-Editor condition

The repository's real-host run instructions SHALL state that a Unity Editor open on an unrelated project shares the platform default per-user Editor log, that this invalidates byte-offset log observation, and that host-private logging is what makes the suite safe to run in that condition. A contributor SHALL be able to recognize the symptom from the instructions rather than by bisecting the product.

#### Scenario: Contributor reads the real-host prerequisites

- **WHEN** a contributor consults the real-host run instructions
- **THEN** the instructions describe the shared-default-log condition and its effect on log observation
- **AND** the instructions state how the host's log is isolated from it

#### Scenario: Contributor diagnoses an observation timeout

- **WHEN** a real-host log-observation case fails with a wait timeout
- **THEN** the instructions let the contributor distinguish an invalidated log source from a product regression

### Requirement: Real-host run instructions document host-required Unity launch arguments

The repository's real-host run instructions SHALL state how a contributor supplies Unity launch arguments that a particular validation host needs in order for CLI auto-launch to succeed (for example a graphics API switch), including the ambient environment variable `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` as a JSON array of strings and its relationship to CLI-driven Editor launch.

#### Scenario: Contributor prepares a host that needs an extra Unity switch

- **WHEN** a contributor consults the real-host run instructions for a host that cannot start without an extra Unity argument
- **THEN** the instructions name `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS`
- **AND** the instructions show a JSON-array example such as `["-force-gles30"]`
- **AND** the instructions state that CLI auto-launch of the host picks the value up without per-command flags

