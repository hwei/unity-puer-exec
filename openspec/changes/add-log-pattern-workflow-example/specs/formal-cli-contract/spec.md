## MODIFIED Requirements

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

#### Scenario: Agent reads help for ordinary log-pattern verification

- **WHEN** an agent reads the published help surface for a project-scoped workflow that verifies success through ordinary Unity log output rather than a result marker
- **THEN** the help surface exposes a first-class workflow example for `exec` plus `wait-for-log-pattern`
- **AND** that example shows capturing `log_offset` before starting `wait-for-log-pattern --start-offset ...`
- **AND** the help surface does not force the agent to infer the full ordinary log-verification path only from scattered command-level prose

#### Scenario: Agent reads help for exec script authoring

- **WHEN** an agent reads `exec --help` or an exec authoring example
- **THEN** help shows the required default-exported module entry shape
- **AND** help explains that immediate return values populate top-level `result`
- **AND** help explains that Promise return values are rejected instead of implicitly awaited
