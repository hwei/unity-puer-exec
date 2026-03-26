# Formal CLI Contract — Delta

## MODIFIED Requirements

### Requirement: Accepted project-scoped exec responses include an explicit continuation hint
When a project-scoped `exec` response enters a non-terminal accepted state, the formal CLI SHALL make the next action explicit enough for a medium-capability agent to follow directly. The default accepted response SHALL include a `next_steps` array with multiple follow-up candidates rather than a single `next_step` object. The first candidate for project-scoped execution SHALL point to `wait-for-exec` with the same `request_id`, and additional candidates SHALL cover alternative observation paths with `when` hints.

#### Scenario: Caller receives a running project-scoped exec response
- **WHEN** `unity-puer-exec exec --project-path ...` returns `status = "running"`
- **THEN** the response includes the accepted `request_id`
- **AND** the response includes a `next_steps` array with at least three candidates
- **AND** the first candidate is `wait-for-exec` with a concrete `argv` including the selector and `request_id`
- **AND** additional candidates include `wait-for-result-marker` and `wait-for-log-pattern` with `when` hints describing when each is appropriate

#### Scenario: Continuation hint stays machine-usable and separate from script result data
- **WHEN** a project-scoped `exec` response includes continuation guidance
- **THEN** the `next_steps` array lives at the top level of the response rather than inside script-authored `result`
- **AND** each candidate includes at minimum a `command` identity and a `when` hint
- **AND** candidates with sufficient context include a full `argv` form that a caller can follow directly

### Requirement: Help is sufficient for agent discovery
Top-level and per-command help SHALL describe the single-entry model, the flat command list, selector exclusivity, workflow examples, key success states, expected non-success states, and minimal invocation examples without requiring repository skill docs as the primary discovery path. When a workflow may return `running`, help SHALL not imply that machine-usable correlation metadata is always present immediately; examples SHALL describe the accepted script-driven way to make correlation ids available when earlier observation is needed. Help for common project-scoped tasks SHALL prioritize the shortest effective workflow so medium-capability agents can identify the preferred path with minimal unnecessary exploration.

Help for `exec` SHALL describe the new module-shaped entry contract, the required default export, the synchronous immediate-result rule, and the fact that Promise-returning entry functions fail explicitly. Help SHALL not continue presenting fragment-style `return ...;` snippets or validation-specific helper APIs as the normal public script surface.

Per-command `--help-status` output SHALL include situation-level explanations for each non-success status so agents can query status meanings independently of runtime guidance.

#### Scenario: Agent reads help to discover normal workflow

- **WHEN** an agent reads `unity-puer-exec --help`
- **THEN** help explains the normal `exec` plus result-marker observation workflow
- **AND** help also explains readiness, observation, and stopped-state workflows
- **AND** the preferred project-scoped path is easy to identify without scanning secondary command flows first

#### Scenario: Agent reads help for a long-running result-marker workflow

- **WHEN** an agent reads command help or examples for a long-running `exec` workflow
- **THEN** help explains how a script deliberately exposes `correlation_id` and result-marker output before `wait-for-result-marker`
- **AND** help does not imply that `running` automatically includes terminal async result data

#### Scenario: Agent reads help for ordinary log-pattern verification

- **WHEN** an agent reads the published help surface for a project-scoped workflow that verifies success through ordinary Unity log output rather than a result marker
- **THEN** the help surface exposes a first-class workflow example for `exec` plus `wait-for-log-pattern`
- **AND** that example shows reading `log_range.start` from the `exec` response and passing it to `wait-for-log-pattern --start-offset ...`
- **AND** the help surface does not force the agent to infer the full ordinary log-verification path only from scattered command-level prose

#### Scenario: Agent reads help for exec script authoring

- **WHEN** an agent reads `exec --help` or an exec authoring example
- **THEN** help shows the required default-exported module entry shape
- **AND** help explains that immediate return values populate top-level `result`

#### Scenario: Agent queries help-status for situation explanations

- **WHEN** an agent invokes `<command> --help-status`
- **THEN** the output includes a situation explanation for each non-success status
- **AND** the explanations are sufficient for the agent to understand the predicament without needing runtime `situation` fields
