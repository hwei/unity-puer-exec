## MODIFIED Requirements

### Requirement: Repository-local scratch artifacts stay out of normal working paths

The repository SHALL provide a local-only place for transient validation probes and scratch scripts so ad hoc artifacts do not accumulate in normal source locations. Repository guidance SHALL direct local scratch artifacts into `.tmp/`, and git ignore rules SHALL keep that directory out of normal version control operations.

#### Scenario: Agent needs a temporary validation script

- **WHEN** an agent creates a short-lived probe or scratch script for local validation
- **THEN** the artifact is placed under `.tmp/`
- **AND** that directory does not create normal git tracking noise
