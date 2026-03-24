## ADDED Requirements

### Requirement: Prompt B compile recovery can be evaluated as a distinct workflow-improvement target
The repository SHALL allow Prompt B validation to measure whether the post-C#-write compile-recovery path becomes more deterministic and less recovery-heavy over time.

#### Scenario: Contributor validates a Prompt B compile-recovery improvement
- **WHEN** a contributor reruns Prompt B after a change aimed at post-write compile recovery
- **THEN** the durable record states whether the run still needed an explicit recovery step after generating the C# script
- **AND** the comparison judges whether the new workflow is closer to `clean` or remains merely `recoverable`
- **AND** the evaluation keeps the archived Prompt B wording unchanged for historical comparability
