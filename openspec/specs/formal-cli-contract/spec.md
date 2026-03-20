# Formal CLI Contract

## Purpose

Define the durable machine-facing contract for the `unity-puer-exec` CLI, including command surface, selector rules, log-driven long-running observation, structured output, exit codes, and help discoverability.
## Requirements
### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `wait-for-exec`, `wait-for-result-marker`, `get-log-source`, `exec`, and `ensure-stopped`.

#### Scenario: Agent discovers the CLI surface

- **WHEN** repository docs or help describe the CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are described only as compatibility paths, not as the authoritative surface
- **AND** transitional aliases remain thin adapters over the formal command behavior rather than separate feature-bearing command trees

### Requirement: Selector-driven commands use mutually exclusive addressing

Selector-driven commands SHALL accept exactly one of `--project-path` or `--base-url`. Supplying both MUST be treated as a usage error. Project-path resolution SHALL follow the repository-wide deterministic resolution order.

#### Scenario: Caller supplies both selectors

- **WHEN** a selector-driven command receives both `--project-path` and `--base-url`
- **THEN** the command reports a usage error
- **AND** machine-readable output surfaces `address_conflict` when structured output is produced

### Requirement: `wait-until-ready` is the explicit readiness shortcut

`wait-until-ready` SHALL act as the explicit readiness-oriented command. In project-path mode it MAY discover or prepare Unity enough for normal use. In base-url mode it SHALL confirm readiness of the directly addressed service without taking ownership of Unity launch. When project-path mode detects an already-open or already-recovering editor for the same target project, it SHALL prefer recovering or reusing that project-scoped runtime instead of blindly starting a competing second Unity launch. If the CLI cannot safely recover or confirm ownership for the target project, it SHALL return a machine-readable non-success result instead of relying on a Unity-native duplicate-open dialog as the primary behavior.

#### Scenario: Project-scoped readiness is requested

- **WHEN** `wait-until-ready --project-path ...` is invoked
- **THEN** the command may discover an existing session or prepare Unity until the target becomes usable
- **AND** a successful result reports `result.status = "recovered"`

#### Scenario: Same project is already open during readiness recovery

- **WHEN** `wait-until-ready --project-path ...` targets a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI reuses or waits for that project-scoped instance instead of starting a competing second launch
- **AND** the command does not treat a Unity-native duplicate-open dialog as the authoritative machine outcome

#### Scenario: Project-scoped launch ownership cannot be established safely

- **WHEN** the CLI cannot safely determine whether the addressed project is already owned by another Unity launch attempt or open editor instance
- **THEN** the command returns a machine-readable non-success result describing the launch-conflict condition
- **AND** the caller can branch on that result without scraping prose dialog text

### Requirement: `exec` is the primary work command

`exec` SHALL send JavaScript to the Unity-side execution service. It SHALL accept exactly one selector and exactly one script input source. In project-path mode it MAY implicitly prepare Unity enough to satisfy the request. In base-url mode it SHALL target an already chosen service without owning Unity launch. When project-path mode needs to prepare Unity, it SHALL follow the same duplicate-launch avoidance and project-scoped recovery rules as `wait-until-ready`.

For accepted script input, `exec` SHALL treat the provided source as module-shaped entry source rather than as an injected async function-body fragment. The source SHALL provide a default-exported entry function used as the exec entrypoint.

#### Scenario: Project-scoped execution is requested

- **WHEN** `exec --project-path ...` is invoked with valid script input
- **THEN** the command may prepare Unity as needed for the execution request
- **AND** the command returns either `status = "completed"` or `status = "running"`

#### Scenario: Project-scoped exec encounters an already-open target project

- **WHEN** `exec --project-path ...` needs readiness work for a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI applies the same project-scoped reuse or conflict behavior as `wait-until-ready`
- **AND** it does not initiate a blind second launch for the same project

#### Scenario: Caller submits a legacy fragment-style script

- **WHEN** `exec` receives script content that does not satisfy the required module-shaped default-export entry contract
- **THEN** the command fails explicitly instead of treating the content as an implicit async function body fragment
- **AND** the published contract does not describe fragment-style scripts as supported input

### Requirement: Exec responses expose a recoverable request identity

The formal CLI SHALL expose a public `request_id` for each accepted `exec` attempt so callers can reason about timeout recovery without depending only on transport success or script-authored correlation data. The CLI SHALL generate a fresh `request_id` automatically for normal use and SHALL also allow the caller to supply an explicit `--request-id` for recovery or idempotent replay.

#### Scenario: Caller receives an accepted exec response

- **WHEN** a caller invokes `unity-puer-exec exec ...` and the request is accepted by the execution service
- **THEN** the response includes a public top-level `request_id` that can be used for later recovery or observation
- **AND** the request identity is part of the formal CLI contract rather than an internal-only detail

#### Scenario: Caller omits an explicit request identity

- **WHEN** a caller invokes `unity-puer-exec exec ...` without `--request-id`
- **THEN** the CLI generates a fresh `request_id` before submission
- **AND** the effective `request_id` is still returned in the accepted response

### Requirement: Exec request identity is caller-owned and idempotent

The formal CLI SHALL treat `request_id` as a caller-owned idempotency key for top-level `exec`. Reusing the same `request_id` with an equivalent execution request SHALL recover or replay the same request state without duplicate execution. Reusing the same `request_id` with a materially different execution request SHALL fail explicitly.

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

### Requirement: Exec timeout handling distinguishes retry from recovery

The formal CLI SHALL define how callers distinguish between safe retry and recovery-oriented follow-up after `exec` returns `not_available`, transport timeout, `running`, or another ambiguous non-terminal condition.

#### Scenario: Caller hits an ambiguous exec timeout

- **WHEN** `unity-puer-exec exec ...` ends in a transport-level timeout or equivalent ambiguous availability failure
- **AND** the caller knows the `request_id` used for that attempt
- **THEN** the published contract explains that the caller should recover with the same `request_id` rather than blindly starting a fresh request
- **AND** the published contract explains how to recover or query the state of a possibly accepted request

#### Scenario: Caller intentionally starts a new request after ambiguity

- **WHEN** a caller chooses a fresh `request_id` after an ambiguous timeout on a side-effecting script
- **THEN** the published contract treats that action as a new execution attempt rather than as recovery
- **AND** help warns that doing so may duplicate side effects if the original request had already been accepted

### Requirement: Exec exposes a single-active-request contract

The formal CLI SHALL expose at most one active top-level `exec` request at a time. The service SHALL not silently queue a second different top-level request while another one is still active.

#### Scenario: Different request arrives while another exec request is active

- **WHEN** the execution service already has an active top-level `exec` request for `request_id = A`
- **AND** the caller submits a new top-level `exec` request with a different `request_id = B`
- **THEN** the command returns a machine-readable `busy` result
- **AND** the service does not hide the conflict behind an implicit queue

### Requirement: Wait-for-exec continues an accepted request by request identity

The formal CLI SHALL provide a dedicated `wait-for-exec` follow-up surface that continues or queries an accepted request by `request_id` without resubmitting script content.

#### Scenario: Caller follows up on a running request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R`
- **THEN** the command reports the current known state of `R` using `running`, `completed`, or `failed`
- **AND** the caller does not need to resend the original script body

#### Scenario: Caller follows up on a missing request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R` and the addressed service has no recoverable record for `R`
- **THEN** the command returns a machine-readable `missing` result
- **AND** the contract does not require the service to distinguish whether `R` was never accepted, was lost with a replaced service instance, or aged out of retention

### Requirement: Async execution remains machine-usable without continuation tokens

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL provide enough machine-readable information for a caller to observe the intended long-running work, including an explicit opt-in path for returning the observation start offset used by result-marker waiting. When that opt-in path is requested, `exec` SHALL return top-level `log_offset` consistently for both `completed` and `running` responses. That `log_offset` SHALL be measured against the same log source consumed by `wait-for-log-pattern` and `wait-for-result-marker`, so callers can rely on it as an observation checkpoint. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The extraction modes that return plain text and parsed JSON SHALL be mutually exclusive. The CLI SHALL provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

The `exec` entry function SHALL return an immediate JSON-serializable value for top-level `result`. The runtime SHALL NOT automatically await Promise or thenable return values from the default-exported entry function. Promise- or thenable-returning entry functions MUST fail explicitly so long-running async work continues to use result-marker observation instead of implicit return awaiting.

#### Scenario: Long-running script uses a correlation-aware result marker

- **WHEN** `exec` starts a script that emits a correlation-specific terminal result marker into the Unity log
- **THEN** the initial `exec` response includes enough machine-readable information for the caller to observe that marker
- **AND** when the caller explicitly requests log offset capture, the response includes the observation start offset
- **AND** the caller can use either `wait-for-log-pattern` with extraction or `wait-for-result-marker` to detect and extract the intended terminal marker without polling a dedicated `get-result` command

#### Scenario: Caller starts observation from the returned checkpoint

- **WHEN** a caller invokes `exec --include-log-offset` and then starts either `wait-for-result-marker` or `wait-for-log-pattern` from the returned `log_offset`
- **THEN** the returned offset is compatible with the observer's actual log source
- **AND** the caller does not need to fall back to scanning from the beginning of the log to find the intended marker

#### Scenario: Alias ignores non-matching marker candidates while waiting

- **WHEN** `wait-for-result-marker` observes lines with the standard marker prefix but the extracted JSON is invalid or the `correlation_id` does not match the requested value
- **THEN** those lines are treated as non-matching candidates rather than terminal command failures
- **AND** the command continues waiting until a matching marker is found or the normal wait termination condition is reached

#### Scenario: Entry function returns a Promise

- **WHEN** the default-exported exec entry function returns a Promise or thenable
- **THEN** `exec` fails explicitly with a machine-readable error
- **AND** the contract does not treat Promise return values as an implicit long-running completion channel

### Requirement: Session identity is not tied only to result continuation

If session identity checking is needed for safe execution or observation, the formal CLI SHALL expose it as a command-level guard rather than as behavior unique to token-driven continuation. Commands that support session guards SHALL fail explicitly when the addressed session does not match the expected session.

#### Scenario: Caller requires same-session observation

- **WHEN** a caller starts work and later waits with an explicit expected session identity
- **THEN** the relevant command reports a machine-readable failure if the addressed session no longer matches
- **AND** the CLI does not silently treat a replacement session as equivalent

#### Scenario: Caller does not require same-session observation

- **WHEN** a caller waits for a result marker without providing an expected session identity
- **THEN** the command may continue observing based on the selected log source and other supplied filters
- **AND** the absence of a session guard does not itself count as a usage error

### Requirement: Observation and stop commands keep their boundary

`wait-for-log-pattern` and `get-log-source` SHALL remain observation commands. `ensure-stopped` SHALL remain the stopped-state command. Observation commands MUST NOT imply Unity launch ownership, and `ensure-stopped` in base-url mode MUST NOT kill the target.

#### Scenario: Agent checks observable log source

- **WHEN** `get-log-source` succeeds
- **THEN** the result reports `result.status = "log_source_available"`
- **AND** the payload includes stable `result.source`

#### Scenario: Agent ensures a base-url target is stopped

- **WHEN** `ensure-stopped --base-url ...` is invoked
- **THEN** the command may inspect state only
- **AND** it does not perform kill behavior against that direct-service target

### Requirement: Log source resolution supports custom project-scoped paths

CLI log-related commands SHALL support an effective Unity log source that is not limited to the platform default Editor log path. After a valid `session_marker` exists, the CLI SHALL treat the session artifact as the authoritative source for `effective_log_path`. Before a valid `session_marker` exists, callers that depend on a non-default log location SHALL provide `--unity-log-path`; otherwise the CLI MAY fall back to the platform default path.

#### Scenario: Post-session observation uses the artifact log path

- **WHEN** a valid session artifact exists with both `session_marker` and `effective_log_path`
- **THEN** `get-log-source` reports that effective path
- **AND** log-observation commands use the same path for waiting and extraction

#### Scenario: Pre-session observation requires an explicit non-default path

- **WHEN** a caller relies on a non-default Unity log path before a valid `session_marker` exists
- **THEN** the caller provides `--unity-log-path` on the log-related command
- **AND** the CLI uses that explicit path instead of the platform default path

### Requirement: Launch-driven sessions can request a custom Unity log path

When `unity-puer-exec` launches Unity for a project-scoped workflow, the CLI SHALL support a caller-controlled path for the Unity Editor log so launch-driven sessions can intentionally avoid the default log location.

#### Scenario: Caller requests a custom log file during launch

- **WHEN** a caller invokes a launch-driven command with `--unity-log-path <path>`
- **THEN** Unity is launched with that log-path override
- **AND** before `session_marker` is available, later log-related commands may continue providing the same `--unity-log-path`
- **AND** once `session_marker` exists, the session artifact records `effective_log_path` so later commands can omit the flag

### Requirement: Formal command results are machine-readable JSON

All formal command results SHALL be machine-readable JSON. Successes and expected non-success machine states that an agent can branch on MUST be emitted on stdout. stderr SHALL be reserved for unstructured usage text or unexpected process-level diagnostics.

#### Scenario: Agent consumes a branchable machine state

- **WHEN** a formal command returns an expected non-success machine state such as `running`, `compiling`, `not_available`, `no_observation_target`, or `not_stopped`
- **THEN** stdout carries the authoritative JSON payload
- **AND** the payload includes stable top-level fields for that command family

### Requirement: Exit codes remain part of the formal machine contract

The CLI SHALL preserve the baseline exit-code model for successful completion, expected machine states, usage errors, and unexpected failures so callers can branch without parsing prose diagnostics.

#### Scenario: Expected machine state completes without success

- **WHEN** a command returns an expected machine state such as `running`, `compiling`, `not_available`, `session_missing`, `session_stale`, `no_observation_target`, or `not_stopped`
- **THEN** the process exits with the corresponding formal non-zero code instead of collapsing all branchable states into one generic failure code

### Requirement: Help is sufficient for agent discovery

Top-level and per-command help SHALL describe the single-entry model, the flat command list, selector exclusivity, workflow examples, key success states, expected non-success states, and minimal invocation examples without requiring repository skill docs as the primary discovery path. When a workflow may return `running`, help SHALL not imply that machine-usable correlation metadata is always present immediately; examples SHALL describe the accepted script-driven way to make correlation ids available when earlier observation is needed. Help for common project-scoped tasks SHALL prioritize the shortest effective workflow so medium-capability agents can identify the preferred path with minimal unnecessary exploration.

Help for `exec` SHALL describe the new module-shaped entry contract, the required default export, the synchronous immediate-result rule, and the fact that Promise-returning entry functions fail explicitly. Help SHALL not continue presenting fragment-style `return ...;` snippets or validation-specific helper APIs as the normal public script surface.

#### Scenario: Agent reads help to discover normal workflow

- **WHEN** an agent reads `unity-puer-exec --help`
- **THEN** help explains the normal `exec` plus result-marker observation workflow
- **AND** help also explains readiness, observation, and stopped-state workflows
- **AND** the preferred project-scoped path is easy to identify without scanning secondary command flows first

#### Scenario: Agent reads help for a long-running result-marker workflow

- **WHEN** an agent reads command help or examples for a long-running `exec` workflow
- **THEN** help explains how a script deliberately exposes `correlation_id` and result-marker output before `wait-for-result-marker`
- **AND** help does not imply that `running` automatically includes terminal async result data

#### Scenario: Agent reads help for exec script authoring

- **WHEN** an agent reads `exec --help` or an exec authoring example
- **THEN** help shows the required default-exported module entry shape
- **AND** help explains that immediate return values populate top-level `result`
- **AND** help explains that Promise return values are rejected instead of implicitly awaited

### Requirement: Help efficiency improvements are validated against transcript evidence
The repository SHALL evaluate CLI help efficiency changes against transcript-backed validation evidence rather than relying only on maintainers' intuition.

#### Scenario: Contributor proposes a help-surface efficiency change
- **WHEN** a contributor updates the CLI help to reduce agent exploration
- **THEN** the justification cites transcript-backed validation findings
- **AND** follow-up validation compares whether convergence became cleaner for representative tasks

### Requirement: Exec script entry uses a minimal context object

The default-exported exec entry function SHALL receive a single context object. The initial public context SHALL expose `request_id` and `globals`.

`request_id` SHALL match the accepted exec request identity already exposed at the CLI layer. `globals` SHALL be a mutable same-service shared object that remains available across exec requests within the lifetime of the same execution service instance.

#### Scenario: Script reads the accepted request identity

- **WHEN** a script's default-exported entry function reads `ctx.request_id`
- **THEN** it receives the same request identity that the accepted exec response exposes at top level
- **AND** the script can include that identity in its immediate result or marker output

#### Scenario: Script reuses same-service shared state

- **WHEN** multiple exec requests are handled by the same execution service instance
- **THEN** the script-visible `ctx.globals` object remains shared across those requests
- **AND** the contract does not describe that object as durable across service restart or replacement

