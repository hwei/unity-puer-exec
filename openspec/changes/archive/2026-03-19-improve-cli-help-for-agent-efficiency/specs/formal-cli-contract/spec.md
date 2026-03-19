## MODIFIED Requirements

### Requirement: Help is sufficient for agent discovery

Top-level and per-command help SHALL describe the single-entry model, the flat command list, selector exclusivity, workflow examples, key success states, expected non-success states, and minimal invocation examples without requiring repository skill docs as the primary discovery path. When a workflow may return `running`, help SHALL not imply that machine-usable correlation metadata is always present immediately; examples SHALL describe the accepted script-driven way to make correlation ids available when earlier observation is needed. Help for common project-scoped tasks SHALL prioritize the shortest effective workflow so medium-capability agents can identify the preferred path with minimal unnecessary exploration.

#### Scenario: Agent reads help to discover normal workflow

- **WHEN** an agent reads `unity-puer-exec --help`
- **THEN** help explains the normal `exec` plus result-marker observation workflow
- **AND** help also explains readiness, observation, and stopped-state workflows
- **AND** the preferred project-scoped path is easy to identify without scanning secondary command flows first

#### Scenario: Agent reads help for a long-running result-marker workflow

- **WHEN** an agent reads help or examples for a workflow that may return `running`
- **THEN** help describes `running` as a normal machine state
- **AND** help does not imply that `correlation_id` is always present before completion

## ADDED Requirements

### Requirement: Help efficiency improvements are validated against transcript evidence
The repository SHALL evaluate CLI help efficiency changes against transcript-backed validation evidence rather than relying only on maintainers' intuition.

#### Scenario: Contributor proposes a help-surface efficiency change
- **WHEN** a contributor updates the CLI help to reduce agent exploration
- **THEN** the justification cites transcript-backed validation findings
- **AND** follow-up validation compares whether convergence became cleaner for representative tasks
