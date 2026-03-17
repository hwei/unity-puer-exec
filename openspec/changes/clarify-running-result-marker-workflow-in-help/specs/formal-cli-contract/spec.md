## MODIFIED Requirements

### Requirement: Help is sufficient for agent discovery

Top-level and per-command help SHALL describe the single-entry model, the flat command list, selector exclusivity, workflow examples, key success states, expected non-success states, and minimal invocation examples without requiring repository skill docs as the primary discovery path. When a workflow may return `running`, help SHALL not imply that machine-usable correlation metadata is always present immediately; examples SHALL describe the accepted script-driven way to make correlation ids available when earlier observation is needed.

#### Scenario: Agent reads help for a long-running result-marker workflow

- **WHEN** an agent reads help or examples for a workflow that may return `running`
- **THEN** help describes `running` as a normal machine state
- **AND** help does not imply that `correlation_id` is always present before completion
