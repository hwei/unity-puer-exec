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

The repository SHALL maintain real-host validation coverage for resolving the reported Unity modal blockers through the CLI.

#### Scenario: Contributor resolves the modified-scenes prompt through the CLI

- **WHEN** the real-host validation workflow triggers the `Scene(s) Have Been Modified` dialog and then invokes `resolve-blocker --action click --hwnd <int> --button "Cancel"`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_modified_scenes_prompt"`
- **AND** follow-up observation can continue through `wait-for-exec` on the original request

#### Scenario: Contributor resolves the save-scene dialog through the CLI

- **WHEN** the real-host validation workflow triggers the `Save Scene` dialog and then invokes `resolve-blocker --action click --hwnd <int> --button "Cancel"`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "save_scene_dialog"`
- **AND** the workflow confirms the dialog is no longer present before treating the resolution as successful

### Requirement: Save-scene blockers are resolved through button targeting

Save-scene dialogs SHALL be resolved through the explicit button-targeted path (`resolve-blocker --action click --hwnd <int> --button "<label>"`) rather than through `--action cancel`, so the validation never demonstrates a default that discards unsaved scene work. The `hwnd` passed to the command SHALL be read from the observed blocker payload, and resolution through `--action cancel` remains validated only for the Safe Mode dialog.

#### Scenario: Cancel is rejected for a save-scene dialog

- **WHEN** the real-host validation workflow triggers a save-scene dialog and then invokes `resolve-blocker --action cancel`
- **THEN** the CLI reports `status = "resolution_failed"`
- **AND** `error = "action_not_supported_for_blocker"`
- **AND** the dialog remains present with unsaved scene changes intact

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

Validation-host preparation tooling SHALL report when the target Unity project contains an embedded package that declares the formal package name and is distinct from the repository-local root injected through `Packages/manifest.json`. Detection SHALL identify an embedded package the way Unity does -- by the `name` declared in a candidate `package.json` among the immediate children of `Packages/` -- and SHALL NOT rely on the directory being named after the package.

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

#### Scenario: Unrelated or unreadable package directories are ignored
- **WHEN** an immediate child of `Packages/` has no `package.json`, has one that cannot be parsed, or declares a different package name
- **THEN** that directory does not contribute to the shadowing report
- **AND** the preparation run completes rather than failing on the unrelated directory

### Requirement: Shadowing report is machine-readable and names all matches

The report SHALL be machine-readable so real-host validation scripts and agents can treat the run as unsafe evidence for repository-local package changes unless the shadowing condition is resolved or intentionally accepted. When more than one embedded directory declares the formal package name, the report SHALL name all of them.

#### Scenario: Multiple shadowing directories are all reported
- **WHEN** more than one immediate child of `Packages/` declares the formal package name and is distinct from the repository-local package root
- **THEN** the preparation result reports shadowing
- **AND** the result names every such directory rather than only the first

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

### Requirement: An expected process state is exercised, not skipped

A process state that an expectation exists to exercise SHALL NOT be treated as a missing prerequisite. In particular, a control port already occupied by another project's Editor is the precondition of the occupied-preferred-port rollover expectation, so that condition SHALL cause the expectation to run, and SHALL NOT cause it to skip.

#### Scenario: Another Editor already occupies the preferred control port

- **WHEN** the real-host validation runs while another project's ready Editor already occupies the preferred control port
- **THEN** the occupied-preferred-port rollover expectation still runs and asserts that the host project's service is ready on a later port in the bounded range
- **AND** it asserts that a project-scoped command with no explicit base URL discovers that later-port endpoint
- **AND** it does not skip, and does not report a pass for any assertion it did not evaluate

### Requirement: Partial staging asserts the observable part

Skipping SHALL be reserved for conditions under which the expectation cannot be evaluated at all -- the gate being disabled, Unity or the host project being absent, the host project being unserviceable, or a required trigger that cannot be staged for reasons outside the suite's control. When an expectation is only partially stageable, the suite SHALL assert the part it can observe and state which part it could not stage, rather than skipping or reporting a pass for the whole expectation.

#### Scenario: A reload-staging sub-assertion cannot be staged

- **WHEN** the real-host validation cannot stage the mid-reload rebind race because the preferred port is already held by something the suite cannot displace
- **THEN** the expectation still asserts the rollover behavior it can observe
- **AND** it records that the mid-reload rebind sub-assertion was not staged, distinguishing "not evaluated" from "passed"

#### Scenario: The suite cannot observe the host's own ready endpoint after a bound launch

- **WHEN** the real-host validation has launched or recovered the host project successfully
- **AND** the suite's own endpoint oracle then cannot find a ready endpoint owned by that project anywhere in the bounded control-port range, after bounded retries
- **THEN** the case fails rather than skipping
- **AND** the failure reports the bound launch outcome and the ports probed, so an endpoint-discovery regression is not reported as a missing prerequisite

### Requirement: Real-host run instructions state how embedded shadowing is cleared

The repository's real-host run instructions SHALL state that renaming an embedded package directory does not stop Unity from loading it, because Unity identifies embedded packages by the `name` declared in `package.json`, and that clearing the shadow requires moving or removing the directory out of `Packages/`. The instructions SHALL name the repository-owned operation that performs that move and the paired operation that reverses it, so a contributor does not have to reconstruct the sequence by hand, and SHALL state that both refuse while the host project is not free.

#### Scenario: Contributor resolves a reported shadowing condition
- **WHEN** a contributor consults the real-host run instructions after a shadowing report
- **THEN** the instructions state that renaming the directory is not sufficient
- **AND** the instructions state that the directory must be moved out of or removed from `Packages/`

#### Scenario: Contributor uses the repository-owned operation instead of a manual move
- **WHEN** a contributor needs the validation host to load repository-local package code
- **THEN** the instructions name the operation that clears the shadow and the one that restores it
- **AND** they state that the pair leaves the host project's version-control status as it was found
- **AND** they state that both refuse while an Editor is serving the host project

### Requirement: Real-host validation observes a log no unrelated Editor can share

Real-host validation SHALL observe the validation host through a log source private to the host project, so a Unity Editor open on an unrelated project cannot share, rotate, or truncate the file the suite reads. A development machine running several Unity projects at once SHALL remain a supported environment for real-host validation.

#### Scenario: Concurrent unrelated Editor does not invalidate observation

- **WHEN** real-host validation runs while an unrelated Unity Editor is open on a different project
- **THEN** the suite observes the validation host through a host-private log
- **AND** log-based assertions reflect output the validation host actually produced

#### Scenario: Host-private log is established without per-command flags

- **WHEN** the suite brings up the validation host
- **THEN** the host-private log is established at launch
- **AND** individual cases do not each have to supply a log-path flag to observe it

#### Scenario: An unrelated Editor does not block the boundary

- **WHEN** the suite establishes its starting boundary while unrelated Unity Editors are running for other projects
- **THEN** those processes do not prevent the boundary from being established

### Requirement: The suite establishes a clean starting boundary from project-local state

The suite SHALL establish its clean starting boundary from project-local state -- the host project's Unity lockfile and published endpoint -- so that a boundary check cannot report the host as stopped while an Editor is still serving it. A case SHALL fail rather than proceed if it would observe a host the suite did not bring up.

#### Scenario: The boundary cannot pass while the host is still serving

- **WHEN** the suite establishes its starting boundary and an Editor is still serving the host project
- **THEN** the boundary does not report the host as stopped
- **AND** no case proceeds against that Editor

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

### Requirement: Real-host validation applies repository-local `.env` launch inputs

Real-host validation SHALL apply repository-local `.env` launch inputs even though it selects the host with an explicit `--project-path`. In particular, `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` loaded from `.env` SHALL reach the Unity launch this repository performs, so a host that needs an extra switch (for example a graphics API switch) can be brought up by the suite without per-command flags.

#### Scenario: Host switch from `.env` reaches the launched Editor

- **WHEN** the validation host needs an extra Unity switch and `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is set only in repository-local `.env`
- **THEN** the Editor the suite launches includes that switch in its argv
- **AND** the suite does not need a per-command flag to supply it

### Requirement: Environment precedence is preserved over .env

Documented precedence SHALL be preserved: a value set explicitly in the process environment overrides the `.env` value, and the explicit project selection is unchanged.

#### Scenario: Process environment overrides `.env`

- **WHEN** `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is present in both the process environment and `.env`
- **THEN** the process-environment value is the one applied to the launch
- **AND** explicitly selecting the host project remains unchanged

#### Scenario: Explicit project selection is unaffected

- **WHEN** a caller supplies `--project-path` for the validation host and `.env` also contains `UNITY_PROJECT_PATH`
- **THEN** the explicit `--project-path` still selects the host
- **AND** loading `.env` does not override the explicit selection

### Requirement: Real-host validation covers ScriptUpdater consent-dialog recovery

The repository SHALL maintain a repeatable real-host validation expectation for the ScriptUpdater consent-dialog recovery path, so the Win32 matcher, the No-button click, and the `warning = "api_updater_declined"` propagation are exercised against a real Unity dialog rather than mocks only. The validation SHALL use a repository-owned host fixture to make Unity show the dialog and SHALL leave the host clean afterwards.

#### Scenario: Contributor validates consent-dialog auto-decline against a real host

- **WHEN** the real-host validation makes the validation host Editor show the ScriptUpdater consent dialog and then runs a CLI wait or exec
- **THEN** the CLI auto-declines the dialog and the command keeps its primary status while also reporting `warning = "api_updater_declined"`
- **AND** the workflow confirms the dialog is gone and project source files were not rewritten (declined, not accepted)

#### Scenario: Non-English dialog text is recorded

- **WHEN** the validation host Editor shows the consent dialog with message text that does not match the English fingerprint
- **THEN** the validation records the observed message text
- **AND** it does not silently report the recovery as verified

### Requirement: An unreproducible consent dialog skips with a diagnosed reason

When the dialog cannot be produced deterministically for the current host or Unity version, the case SHALL skip with a machine-usable diagnosed reason instead of reporting a vacuous pass.

#### Scenario: Consent dialog cannot be triggered on the current host

- **WHEN** the real-host validation cannot make the validation host Editor show the ScriptUpdater consent dialog
- **THEN** the case skips with a diagnosed reason that names the trigger blocker
- **AND** it does not report a pass that would be indistinguishable from a genuine recovery verification

### Requirement: Real-host validation tolerates transient cold-launch failures

Real-host validation SHALL treat a bounded number of transient cold-launch failures as retryable rather than failing a case on the first attempt. Non-launch failures and genuine assertion failures SHALL NOT be retried.

#### Scenario: A cold launch races the previous Editor shutdown

- **WHEN** a real-host case force-stops the host and the next launch begins before the prior Editor has fully released the project
- **THEN** the suite retries the launch within a bounded budget after confirming the boundary is clean
- **AND** a launch that succeeds on retry does not fail the case

#### Scenario: Non-launch failures are not retried

- **WHEN** a real-host case fails for a reason other than bringing the host up (for example an assertion on a completed CLI response)
- **THEN** the suite does not retry the case
- **AND** the original failure is reported directly

### Requirement: Every launch attempt is recorded distinctly

Every attempt SHALL be recorded with enough state to distinguish a flake from a persistent launch regression.

#### Scenario: A persistent regression is not masked

- **WHEN** every launch attempt fails
- **THEN** the case fails with the attempt count and last launch status recorded
- **AND** the failure is not reported as a transient flake

### Requirement: Real-host validation can resolve a modal dialog outside the catalog

The repository SHALL maintain real-host validation coverage for a Unity modal dialog that has no catalog entry, covering both its reporting and its resolution through the explicit button-targeted path. The validation SHALL record whether owner-based modal discrimination correctly excluded non-blocking Editor windows present at the same time.

#### Scenario: Contributor validates an unknown modal dialog

- **WHEN** the real-host validation workflow triggers a Unity modal dialog that matches no catalog entry
- **THEN** follow-up CLI observation reports `status = "modal_blocked"`
- **AND** the observed blocker payload records `blocker.type = "unknown_modal_dialog"`
- **AND** the payload includes `hwnd`, `title`, `body`, and `buttons`

#### Scenario: Contributor resolves an unknown modal dialog through the CLI

- **WHEN** the real-host validation workflow observes an `unknown_modal_dialog` blocker and then invokes `resolve-blocker --action click --hwnd <int> --button "<label>"` with a label from that payload's `buttons`
- **THEN** the CLI reports `result.status = "resolved"`
- **AND** `result.blocker.type = "unknown_modal_dialog"`
- **AND** the workflow confirms the dialog is no longer present before treating the resolution as successful

#### Scenario: Non-blocking Editor windows are not reported

- **WHEN** the real-host validation workflow opens Editor windows that do not block exec, such as `Preferences` or `Project Settings`, while validation observes blockers
- **THEN** CLI observation does not report any of those windows as a modal blocker

### Requirement: Real-host suite cost scales with cases, not with host relaunches

The repository-owned real-host validation workflow SHALL bring the validation host Editor up at most once per suite run and SHALL reuse that Editor across its cases, so adding a case does not add a full Editor launch. Per-case isolation SHALL be achieved by resetting test-owned state between cases -- repository-owned validation temp assets, Editor play mode, and any test-owned session or change-signal state -- rather than by stopping and relaunching the Editor.

#### Scenario: Sequential cases reuse one Editor

- **WHEN** a contributor runs the real-host suite and the first case has brought the
  host up
- **THEN** subsequent cases in the same suite run reuse that Editor
- **AND** the suite does not stop and relaunch the Editor between ordinary cases

#### Scenario: A case does not observe another case's leftovers

- **WHEN** one case leaves repository-owned validation temp assets, a pending refresh
  signal, or an Editor in play mode
- **THEN** the next case starts from a reset state
- **AND** its assertions are not affected by the previous case's leftovers

#### Scenario: The suite still establishes its starting boundary

- **WHEN** the suite begins
- **THEN** it establishes the clean starting boundary from project-local state before
  bringing the host up
- **AND** the boundary rules for lockfile and published endpoint are unchanged from the
  per-case model

### Requirement: Pristine-process cases opt into their own launch boundary

A case that genuinely requires a pristine process (for example batch-mode activation behavior or preferred-port rollover) SHALL be able to opt into its own launch boundary, and SHALL say so rather than silently bypass the shared host.

#### Scenario: A pristine-process case keeps its own boundary

- **WHEN** a case requires a process that the shared Editor cannot provide, such as a
  batch-mode launch or a specific occupied-port condition
- **THEN** that case opts into its own launch and stop boundary
- **AND** it reports its boundary result rather than assuming the shared host

#### Scenario: A host that dies mid-suite is handled explicitly

- **WHEN** the shared Editor exits or stops responding while the suite is running
- **THEN** the workflow either re-establishes the host within its bounded retry budget
  or fails the case with machine-usable launch diagnostics
- **AND** it does not report a pass against a host that was not running

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

### Requirement: Real-host automatic-refresh cases budget the refresh at the compile scale

The repository-owned real-host validation workflow SHALL budget a request that triggers an
automatic refresh with a compile-scale wait, so the CLI's settle-and-resubmit loop reaches
the terminal response the refresh path produces. Such a case SHALL assert the refresh
disclosure on that terminal response and SHALL NOT depend on a continuation fetched by a
different command to carry the refresh decision.

#### Scenario: Refresh-triggering base-url case reaches the terminal exec response

- **WHEN** a real-host case makes a code change that triggers an automatic refresh, then
  runs `exec` against the host's control endpoint
- **THEN** the request is given a compile-scale wait budget
- **AND** the case asserts `refresh.triggered` and the `compile_triggering_change` reason on
  the terminal `exec` response
- **AND** the payload it asserts on is not a `wait-for-exec` continuation

#### Scenario: A request budget shorter than the refresh settle fails the case

- **WHEN** a refresh-triggering request returns a non-terminal response because its wait
  budget ended before the settle completed
- **THEN** the case does not treat a later continuation's payload as evidence that the
  refresh decision was disclosed
- **AND** the case fails with that expectation named

### Requirement: Per-case reset restores the active scene and clears residual modals

The real-host per-case reset SHALL return the shared Editor to a scene state that does not
depend on the previous case, and SHALL clear a residual modal before the next case runs, so a
case observes only the state it staged.

#### Scenario: A scene-dependent case does not inherit the previous scene

- **WHEN** a case needs a specific scene state, for example to raise a save-scene dialog
- **THEN** the case stages that state itself, or the reset restores it
- **AND** a previous case's scene does not change which dialog the case observes

#### Scenario: A residual modal does not distort the next case

- **WHEN** a previous case leaves a modal dialog up
- **THEN** the next case's reset clears it before the case runs
- **AND** the case's dialog assertions observe only the dialogs it staged itself

### Requirement: Real-host probes tolerate the control endpoint's reload window

The real-host harness SHALL probe the control endpoint through a shared helper that tolerates
the endpoint dropping during a domain reload and rebinding, possibly on a different port. A
probe SHALL fail a case only when the endpoint does not return within a bounded window, or when
the case explicitly requires an endpoint that is live at that moment.

#### Scenario: A probe lands inside a domain reload

- **WHEN** a case probes health right after a compile or a play-mode exit with a deferred compile
- **AND** the control endpoint is down for the reload or rebinds to another port
- **THEN** the shared probe re-resolves the endpoint and waits the reload out within its bound
- **AND** the case does not fail on a transport error unrelated to the behavior under test

#### Scenario: The endpoint never returns

- **WHEN** the endpoint does not come back within the probe's bound
- **THEN** the case fails with a message that names the reload window
- **AND** the failure is not masked by an unbounded retry

### Requirement: Validation host wiring declares the package testable

Repository-owned helper tooling that injects `com.txcombo.unity-puer-exec` into a validation host
SHALL ALSO declare the package in the host manifest's `testables` list, because Unity compiles and
discovers a package's own test assemblies only for a testable package. The declaration SHALL be
idempotent and SHALL preserve unrelated `testables` entries.

#### Scenario: Host is wired to the package's own test assemblies

- **WHEN** the validation host manifest is rewritten by repository-owned helper tooling
- **THEN** `Project/Packages/manifest.json` declares `com.txcombo.unity-puer-exec` in `testables`
- **AND** entries already present in `testables` are preserved
- **AND** running the rewrite again does not duplicate the declaration and reports the host as unchanged

### Requirement: Host wiring reports whether the package is testable

Helper tooling SHALL report whether the host declares the package testable, so a host that carries
the dependency without the declaration is not reported as fully wired.

#### Scenario: The host is not treated as wired when the package is not testable

- **WHEN** a host manifest carries the local package dependency but no `testables` declaration
- **THEN** the helper reports the declaration as pending rather than reporting the host as already wired

### Requirement: Real-host exec request ids are unique per invocation

A real-host test that submits an exec SHALL choose a request id that is different on every invocation of that test in the same process. The id SHALL NOT be derived only from the process id.

#### Scenario: The same case runs twice in one process

- **WHEN** a real-host case builds the request id for an exec
- **AND** the same case builds another request id without restarting the process
- **THEN** the two ids are different
- **AND** the second submission is a new execution rather than a replay of the first

### Requirement: A real-host refresh trigger is staged with a watched compile-triggering extension

The repository-owned real-host validation workflow SHALL stage a refresh trigger as a file whose extension the Editor's change signal watches, and SHALL reject a probe name outside that set before any Editor launch. A change signal that never becomes pending SHALL fail with the watched extensions and the observed `skipped_reason` named, so a mistyped probe is distinguishable from a genuine detection failure.

#### Scenario: A probe without a watched extension is rejected locally

- **WHEN** a real-host case stages a refresh trigger whose name does not end in a watched extension
- **THEN** the staging helper fails with the watched extensions named
- **AND** no Editor launch and no validation-host write occurs for that probe

#### Scenario: A change signal that never becomes pending names the cause

- **WHEN** a real-host case waits for a staged change to be observed as pending and the Editor never reports it as pending
- **THEN** the failure message names the watched extensions: C# sources, assembly definitions and references, and compiler response files
- **AND** it reports the observed `skipped_reason` from the last health payload

#### Scenario: A dropped control endpoint keeps its own failure message

- **WHEN** the control endpoint never returns a health payload during the pending wait
- **THEN** the failure names the unreachable control endpoint rather than the change signal

#### Scenario: A correctly staged probe still crosses a real refresh

- **WHEN** a real-host case stages a probe with a watched extension, waits for it to be observed as pending, and then runs `exec` against the host's control endpoint
- **THEN** the case proceeds unchanged and asserts the refresh disclosure on the terminal `exec` response

### Requirement: Run instructions state the release-time host package identity rule

The repository's real-host run instructions SHALL state that a host loading an embedded copy of the package must declare the release candidate version before a real-host run counts as evidence for the release, what happens when it does not, and how the release helper reports or aligns it.

#### Scenario: Contributor reads the prerequisites before a release

- **WHEN** a contributor consults the real-host run instructions before preparing a release
- **THEN** the instructions state that a host loading an embedded package copy must declare the version being released
- **AND** the instructions state that the release helper refuses real-host validation when the loaded version differs, and names the loaded path and both versions
- **AND** the instructions state that the helper aligns the version only when explicitly asked and only when the copy's content matches the repository package, ignoring `CLI~/` and line-ending differences
- **AND** the instructions state that the helper refuses, rather than skips, real-host validation when no usable validation host is configured
- **AND** the instructions state that aligning the host `package.json` makes an open Editor re-resolve packages, and that the real-host suite relaunches the Editor regardless

#### Scenario: Host is wired only through the file dependency

- **WHEN** a contributor's host has no embedded package copy and loads the package through a manifest `file:` dependency pointing at this repository's package
- **THEN** the instructions state that no host version action is required, because the loaded package is the repository package

### Requirement: Validation host preparation can clear and restore an embedded shadow

Validation-host preparation tooling SHALL offer a paired operation that clears an embedded package
shadow by moving every shadowing directory out of `Packages/` into a host-local backup, and restores
it by the exact inverse move. Neither direction SHALL delete anything, and neither SHALL perform a
version-control operation on the host project. Both SHALL report machine-readably which action they
took, the backup path involved, and the resulting shadowing value.

#### Scenario: Clearing moves every shadowing directory out of Packages

- **WHEN** a contributor asks preparation to clear an embedded shadow
- **AND** one or more immediate children of `Packages/` declare the formal package name and are
  distinct from the repository-local package root
- **THEN** the tool moves each such directory into a host-local backup outside `Packages/`
- **AND** it reports the cleared status, the backup path, and every directory it moved
- **AND** a following preparation run reports `embedded_package_shadowing = false`

#### Scenario: Restoring is the exact inverse

- **WHEN** a contributor asks preparation to restore a previously cleared embedded package
- **AND** the backup holds the directories the clear moved
- **THEN** the tool moves them back to their original `Packages/` paths
- **AND** the host project's version-control status matches what it was before the clear
- **AND** nothing is deleted in either direction

#### Scenario: Both operations are idempotent

- **WHEN** a contributor asks to clear a host that has no embedded shadow
- **OR** asks to restore a host whose embedded package is already in place
- **THEN** the tool reports an unchanged status rather than failing
- **AND** it writes nothing

#### Scenario: A restore refuses rather than merging into an occupied target

- **WHEN** a contributor asks to restore an embedded package
- **AND** the corresponding `Packages/` child already exists
- **THEN** the tool refuses and names the occupied path
- **AND** it neither merges the two copies nor overwrites either one

#### Scenario: A clear refuses when its backup path is already occupied

- **WHEN** a contributor asks to clear an embedded shadow
- **AND** the backup path for that directory already holds content
- **THEN** the tool refuses and names the occupied backup path
- **AND** it leaves the embedded package where it is

### Requirement: Shadow switching refuses on a host that is not free

The clear and restore operations SHALL refuse when the target host project is not free, decided from
project-local state alone, because moving a package under a live Editor leaves its asset database
describing a package that is no longer there. The tool SHALL report the refusal and the evidence it
used, and SHALL NOT stop an Editor process.

#### Scenario: A live Editor serving the host blocks the operation

- **WHEN** a contributor asks to clear or restore an embedded shadow
- **AND** the host project's own lockfile is held or its Editor has published a control endpoint
- **THEN** the tool refuses and names the project-local evidence it used
- **AND** it moves nothing
- **AND** it does not terminate any Editor process

#### Scenario: A free host proceeds

- **WHEN** the host project's lockfile is not held and no Editor has published an endpoint for it
- **THEN** the requested clear or restore proceeds

### Requirement: Shadow switching is previewable without writing

The clear and restore operations SHALL honour the existing preview mode, reporting what they would
move and where without writing anything, so an operator can inspect the effect on a host project
before allowing a move of files that project tracks.

#### Scenario: Preview reports the intended moves

- **WHEN** a contributor asks to clear or restore an embedded shadow in preview mode
- **THEN** the tool reports the directories it would move and the backup path it would use
- **AND** it writes nothing and reports the preview status rather than a performed one

### Requirement: Validation host manifest wiring is reversible

When preparation tooling first rewrites a host's `Packages/manifest.json`, it SHALL save the original `manifest.json` and, if present, `packages-lock.json` into a host-local backup outside `Packages/`. A restore operation SHALL move both back. Neither direction SHALL delete anything or perform a version-control operation on the host, and both SHALL report machine-readably the action taken and the backup path.

#### Scenario: First rewrite saves the originals

- **WHEN** preparation rewrites a host manifest that has no existing manifest backup
- **THEN** the original `manifest.json` and `packages-lock.json` are saved into the host-local backup before the rewrite
- **AND** the report names the backup path

#### Scenario: A repeated rewrite keeps the first backup

- **WHEN** preparation rewrites a host manifest that already has a manifest backup
- **THEN** the existing backup is left untouched, so it still holds the pre-preparation originals

#### Scenario: Restore returns the host to its pre-preparation files

- **WHEN** a contributor asks preparation to restore the manifest
- **AND** a manifest backup exists
- **THEN** the tool moves the saved `manifest.json` and `packages-lock.json` back into `Packages/`
- **AND** the host's version-control status for those files matches what it was before the first preparation
- **AND** it reports the restored status

#### Scenario: Restore with nothing to restore is unchanged

- **WHEN** a contributor asks to restore the manifest
- **AND** no manifest backup exists
- **THEN** the tool reports an unchanged status rather than failing
- **AND** it writes nothing

### Requirement: Manifest restore refuses to overwrite foreign edits

The manifest restore SHALL refuse when the current `manifest.json` differs from the content preparation last wrote, naming the reason, so that edits made after preparation are never silently discarded.

#### Scenario: Manifest edited after preparation

- **WHEN** a contributor asks to restore the manifest
- **AND** `manifest.json` no longer matches the content preparation last wrote
- **THEN** the tool refuses and states that the manifest changed since preparation
- **AND** it moves nothing

#### Scenario: Regenerated lock file does not block restore

- **WHEN** Unity has regenerated `packages-lock.json` after preparation
- **AND** `manifest.json` still matches what preparation wrote
- **THEN** the restore proceeds and replaces the regenerated lock file with the saved original

### Requirement: Manifest restore follows the shadow-switch safety rules

The manifest restore SHALL refuse while the host is not free, decided from the same project-local evidence that shadow switching uses, and SHALL honour preview mode by reporting what it would move without writing.

#### Scenario: A live Editor blocks the restore

- **WHEN** a contributor asks to restore the manifest
- **AND** the host project's lockfile is held or its Editor has published a control endpoint
- **THEN** the tool refuses, names the evidence, and moves nothing

#### Scenario: Preview reports the intended restore

- **WHEN** a contributor asks to restore the manifest in preview mode
- **THEN** the tool reports the files it would move and the backup path
- **AND** it writes nothing and reports the preview status

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

### Requirement: Real-host validation covers ES module import resolution and explicit JsEnv reset

The real-host suite SHALL cover `exec --import-base-url` resolving a relative ES module import
against a live Editor, and SHALL cover `exec --reset-jsenv-before-exec` observably clearing
JavaScript environment state. The reset case SHALL distinguish the explicit flag from the
default same-invocation recovery of a changed module, so it cannot pass without the flag being
exercised. Both cases SHALL run against the shared host device rather than adding an Editor
launch.

#### Scenario: A relative import resolves through a filesystem base URL

- **WHEN** a real-host case runs `exec --code` whose entry module imports a sibling module by
  relative specifier
- **AND** `--import-base-url` names a filesystem directory containing that module
- **THEN** the request reaches a terminal `completed` status
- **AND** the imported module's exported value appears in the response `result`, proving
  resolution happened rather than merely that no error was raised

#### Scenario: An explicit reset is distinguishable from default staleness recovery

- **WHEN** a real-host case runs `exec --reset-jsenv-before-exec` after an earlier exec stored
  state in `ctx.globals`
- **AND** the module source is unchanged between the two requests
- **THEN** the stored state is gone in the second request
- **AND** the case would fail if the explicit reset silently stopped happening, which a
  changed-module-only assertion would not detect because default staleness recovery already
  reloads a changed module

#### Scenario: The cases do not add an Editor launch

- **WHEN** the real-host suite runs with these cases present
- **THEN** they execute against the shared host device
- **AND** the suite's Editor launch count is unchanged from before the cases were added

#### Scenario: The cases leave no residue in the host project

- **WHEN** the import and reset cases finish
- **THEN** any module fixture they wrote is removed by the suite's existing per-case cleanup
- **AND** a host project under version control reports no new or modified tracked file from the
  run

#### Scenario: Coverage holds on every supported PuerTS major

- **WHEN** the real-host suite runs against a host whose `com.tencent.puerts.core` is a
  supported major
- **THEN** the import and reset cases pass on that host
- **AND** a failure on one supported major and not another is reported as a version-specific
  regression rather than as a host problem

### Requirement: A case asserts the product's report for a dialog the product dismisses

When a real-host case stages a dialog that the CLI dismisses automatically, the case SHALL
assert the product's own report of that dismissal rather than inspecting the dialog's window
state after the command. A post-command window read SHALL NOT be the evidence for an
auto-recovered dialog, because the command under test is what removes the dialog.

#### Scenario: Auto-recovered dialog is asserted through the product report

- **WHEN a real-host case stages the ScriptUpdater consent dialog and runs a CLI command
- **THEN the case asserts the command's `warning = "api_updater_declined"` and its
  `warning_detail`
- **AND it does not assert that the dialog is still visible after the command

#### Scenario: An absent dialog is not reported as an untriggered one

- **WHEN a post-command observation finds no auto-recovered dialog
- **AND the same command reported that it declined one
- **THEN the case treats the dialog as triggered and dismissed
- **AND it does not skip with a "could not be triggered" reason

### Requirement: A case may observe a dialog the product leaves alone

When a real-host case stages a dialog the CLI does not dismiss automatically, the case SHALL
continue to assert on the observed dialog. Such a dialog SHALL NOT be treated as an
auto-recovered dialog merely because a CLI command ran before the observation.

#### Scenario: Catalog dialogs are still observed directly

- **WHEN a real-host case stages a save-scene, modified-scene, or unknown prompt dialog
- **AND runs a CLI command before inspecting window state
- **THEN the case observes the staged dialog and asserts on its payload
- **AND no guard treats that observation as a race

### Requirement: The suite structure is guarded against reintroducing the race

The repository SHALL carry a guard that fails when a real-host case combines an auto-recovered
dialog with a post-command window read. The guard SHALL derive its inventory from the real-host
suite source rather than from a hand-maintained list, so a new case is covered without a second
place to update.

#### Scenario: A reintroduced race fails the guard

- **WHEN a real-host case stages an auto-recovered dialog and then reads window state after a
  CLI command
- **THEN the guard reports that case by name
- **AND the default mocked suite fails without needing an Editor

#### Scenario: A sound post-command observation passes the guard

- **WHEN a real-host case stages a dialog the product does not dismiss and reads window state
  after a command
- **THEN the guard reports no violation for that case

### Requirement: The Win32 double models cross-process text reads

The mocked `user32` double SHALL be able to reproduce the difference between reading a window's
text with `GetWindowTextW` and with `WM_GETTEXT`. It SHALL allow a fixture to mark a control as
answering `GetWindowTextW` with a cached stub while `WM_GETTEXT` returns the control's real text.

#### Scenario: A fixture reproduces the measured foreign-control stub

- **WHEN a fixture marks a control as returning a cached `GetWindowTextW` value
- **THEN `GetWindowTextW` and `GetWindowTextLengthW` report that cached value
- **AND `WM_GETTEXT` on the same handle reports the control's real text

#### Scenario: A control that ignores the message is expressible

- **WHEN a fixture marks a control as not answering `WM_GETTEXT`
- **THEN the double reports that the message went unanswered
- **AND the production code's fallback path is exercised rather than an empty body being
  produced

### Requirement: The mocked layer pins the cross-process divergence

A mocked test SHALL assert that the divergence above is expressible through the double and that
the product reads the message rather than the stub. The assertion SHALL fail if the double is
simplified to answer both calls identically.

#### Scenario: Collapsing the two reads fails a test

- **WHEN the double is changed so `GetWindowTextW` and `WM_GETTEXT` return the same text for a
  foreign control
- **THEN a named test fails
- **AND its message names the cross-process read as the thing no longer covered

### Requirement: The same-process limitation is stated where fixtures are written

The double's documentation SHALL state which calls it answers with in-process semantics, and
that `GetWindowTextW` is valid only for a same-process window or a top-level window caption.

#### Scenario: A fixture author can see the hazard

- **WHEN a reader opens the fake's module docstring or the model of a text read
- **THEN the cross-process limitation is stated there
- **AND the calls the double answers with in-process semantics are named
