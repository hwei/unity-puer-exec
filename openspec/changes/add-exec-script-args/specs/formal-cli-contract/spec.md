## MODIFIED Requirements

### Requirement: `exec` is the primary work command

`exec` SHALL send JavaScript to the Unity-side execution service. It SHALL accept exactly one selector and exactly one script input source. It MAY also accept caller-supplied script arguments through `--script-args`. In project-path mode it MAY implicitly prepare Unity enough to satisfy the request. In base-url mode it SHALL target an already chosen service without owning Unity launch. When project-path mode needs to prepare Unity, it SHALL follow the same duplicate-launch avoidance and project-scoped recovery rules as `wait-until-ready`. If project-scoped execution is blocked by a Unity-native modal dialog, the CLI SHALL surface a machine-usable blocking result or blocker diagnostics instead of failing only as an unexplained timeout.

#### Scenario: Project-scoped execution is requested

- **WHEN** `exec --project-path ...` is invoked with valid script input
- **THEN** the command may prepare Unity as needed for the execution request
- **AND** the command returns either `status = "completed"` or `status = "running"`

#### Scenario: Project-scoped exec encounters an already-open target project

- **WHEN** `exec --project-path ...` needs readiness work for a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI applies the same project-scoped reuse or conflict behavior as `wait-until-ready`
- **AND** it does not initiate a blind second launch for the same project

#### Scenario: Project-scoped exec is blocked by a modal dialog

- **WHEN** `exec --project-path ...` cannot proceed because Unity Editor is blocked by a native modal dialog
- **THEN** the CLI surfaces a machine-usable blocking result or explicit blocker diagnostics
- **AND** the caller does not need to guess whether the failure was caused by script logic or editor UI state

#### Scenario: Caller queries blocker state after an exec-side stall

- **WHEN** a caller invokes the explicit blocker-query command for a project-scoped Unity Editor instance after an exec-side timeout or stall symptom
- **THEN** the command reports whether a supported modal blocker is currently detected
- **AND** the command does not require the caller to resubmit the blocked exec request

#### Scenario: Supported save-scene blockers are reported with stable types

- **WHEN** project-scoped exec or blocker-query detection observes the supported Windows save-scene dialogs
- **THEN** the machine-readable payload uses `status = "modal_blocked"`
- **AND** `blocker.type` is `save_modified_scenes_prompt` for the `Scene(s) Have Been Modified` dialog
- **AND** `blocker.type` is `save_scene_dialog` for the `Save Scene` file-save dialog
- **AND** `blocker.scope` is `exec`

### Requirement: Exec request identity is caller-owned and idempotent

The formal CLI SHALL treat `request_id` as a caller-owned idempotency key for top-level `exec`. Reusing the same `request_id` with an equivalent execution request SHALL recover or replay the same request state without duplicate execution. Reusing the same `request_id` with a materially different execution request SHALL fail explicitly. Equivalent execution requests SHALL compare the effective target identity, normalized script content, and canonical script-argument object rather than only the raw transport form.

#### Scenario: Caller idempotently replays the same exec request

- **WHEN** a caller invokes `unity-puer-exec exec ... --request-id R` more than once with equivalent execution content and target identity
- **THEN** the service does not start a second execution for `R`
- **AND** the response reports the current or final state of the existing request instead of duplicating side effects

#### Scenario: Caller reuses a request identity for different execution content

- **WHEN** a caller invokes `unity-puer-exec exec ... --request-id R` after `R` has already been associated with materially different execution content or target identity
- **THEN** the command returns a machine-readable `request_id_conflict` result
- **AND** the caller can branch on that result without guessing which request definition won

#### Scenario: Equivalent exec requests ignore CLI input-form differences

- **WHEN** two `exec` attempts use the same effective target identity and the same normalized script content but arrive through different input forms such as `--file`, `--stdin`, or `--code`
- **THEN** the service treats them as the same execution request for `request_id` matching
- **AND** request equivalence is not broken only because the CLI transport form changed

#### Scenario: Equivalent exec requests require matching script arguments

- **WHEN** two `exec` attempts reuse the same `request_id` and target identity with the same normalized script content but different `--script-args` objects
- **THEN** the service treats them as materially different execution requests
- **AND** the command returns `request_id_conflict` instead of silently replaying the earlier request

### Requirement: Wait-for-exec continues an accepted request by request identity

The formal CLI SHALL provide a dedicated `wait-for-exec` follow-up surface that continues or queries an accepted request by `request_id` without resubmitting script content. For project-scoped accepted requests that depend on a local pending artifact, the CLI SHALL treat that artifact as bounded local recovery state rather than as durable unbounded storage. When the accepted request includes caller-supplied script arguments, the bounded local recovery state SHALL preserve those arguments so replayed execution remains equivalent to the accepted request.

#### Scenario: Caller follows up on a running request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R`
- **THEN** the command reports the current known state of `R` using `running`, `completed`, or `failed`
- **AND** the caller does not need to resend the original script body

#### Scenario: Caller follows up on a missing request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R` and the addressed service has no recoverable record for `R`
- **THEN** the command returns a machine-readable `missing` result
- **AND** the contract does not require the service to distinguish whether `R` was never accepted, was lost with a replaced service instance, aged out of retention, or was represented only by a malformed local leftover

#### Scenario: Project-scoped replay preserves script arguments

- **WHEN** a project-scoped `exec --request-id R --script-args '{...}'` is accepted into a non-terminal state that later resumes through `wait-for-exec --request-id R`
- **THEN** the replayed execution uses the same effective script-argument object as the accepted request
- **AND** the caller does not need to restate `--script-args` during `wait-for-exec`

### Requirement: Exec script entry uses a minimal context object

The default-exported exec entry function SHALL receive a single context object. The public context SHALL expose `request_id`, `globals`, and `args`.

`request_id` SHALL match the accepted exec request identity already exposed at the CLI layer. `globals` SHALL be a mutable same-service shared object that remains available across exec requests within the lifetime of the same execution service instance. `args` SHALL be the caller-supplied script-argument object, and when the caller omits `--script-args` the runtime SHALL still expose `ctx.args` as an empty object. Published help for exec script authoring SHALL identify those fields as the guaranteed context surface and SHALL not imply that undocumented fields such as `ctx.project_path` are available. When scripts need project-local file paths, the published guidance SHALL direct callers toward supported Unity or .NET APIs such as `UnityEngine.Application.dataPath` plus `System.IO.Path.GetDirectoryName(...)`.

#### Scenario: Script reads the accepted request identity

- **WHEN** a script's default-exported entry function reads `ctx.request_id`
- **THEN** it receives the same request identity that the accepted exec response exposes at top level
- **AND** the script can include that identity in its immediate result or marker output

#### Scenario: Script reuses same-service shared state

- **WHEN** multiple exec requests are handled by the same execution service instance
- **THEN** the script-visible `ctx.globals` object remains shared across those requests
- **AND** the contract does not describe that object as durable across service restart or replacement

#### Scenario: Script reads caller-supplied arguments

- **WHEN** a caller invokes `exec` with `--script-args` containing a valid JSON object
- **THEN** the default-exported entry function receives that object at `ctx.args`
- **AND** the script does not need a second positional parameter to access caller-supplied arguments

#### Scenario: Script omits caller-supplied arguments

- **WHEN** a caller invokes `exec` without `--script-args`
- **THEN** the default-exported entry function still receives `ctx.args`
- **AND** `ctx.args` is an empty object rather than `null` or `undefined`

## ADDED Requirements

### Requirement: Exec script-argument input is validated before runtime execution

The formal CLI SHALL validate `--script-args` before submitting an exec request. The first version SHALL parse the option as JSON and SHALL require the top-level value to be an object.

#### Scenario: Caller supplies malformed script arguments

- **WHEN** a caller invokes `exec --script-args <text>` and the provided text is not valid JSON
- **THEN** the command fails explicitly before runtime execution begins
- **AND** the machine-readable failure identifies invalid script-argument JSON

#### Scenario: Caller supplies a non-object JSON value

- **WHEN** a caller invokes `exec --script-args <text>` and the provided JSON parses successfully but the top-level value is not an object
- **THEN** the command fails explicitly before runtime execution begins
- **AND** the machine-readable failure identifies that script arguments must be an object
