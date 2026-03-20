## MODIFIED Requirements

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

## ADDED Requirements

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
