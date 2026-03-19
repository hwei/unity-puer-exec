## ADDED Requirements

### Requirement: Change metadata does not replace narrative context
`meta.yaml` SHALL remain machine-readable planning metadata for non-archived changes. Dependency metadata such as `blocked_by` MAY identify prerequisite changes, but it MUST NOT be treated as sufficient by itself to explain the evidence chain, rationale, or inherited findings for follow-up work.

#### Scenario: Maintainer inspects a dependent change
- **WHEN** a maintainer or agent reads `meta.yaml` for a change that depends on earlier work
- **THEN** the metadata exposes machine-readable prerequisite references for tooling
- **AND** repository workflow still expects proposal or design artifacts to explain the human-readable background when that context is necessary
- **AND** the maintainer does not treat dependency metadata alone as the complete explanation of why the change exists
