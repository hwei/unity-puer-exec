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

The repository's real-host run instructions SHALL state that renaming an embedded package directory does not stop Unity from loading it, because Unity identifies embedded packages by the `name` declared in `package.json`, and that clearing the shadow requires moving or removing the directory out of `Packages/`.

#### Scenario: Contributor resolves a reported shadowing condition
- **WHEN** a contributor consults the real-host run instructions after a shadowing report
- **THEN** the instructions state that renaming the directory is not sufficient
- **AND** the instructions state that the directory must be moved out of or removed from `Packages/`

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
