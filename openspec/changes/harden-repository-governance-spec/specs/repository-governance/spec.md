## MODIFIED Requirements

### Requirement: Apply-closeout findings require human discussion before promotion

Apply-closeout findings SHALL be surfaced for human discussion before they are promoted
into durable governance rules, and an executor MUST NOT promote a closeout finding into
repository governance on its own. This requirement restates the constraint that lives in
the durable apply-closeout-review spec as a repository-governance rule and adds no
constraint beyond it; the canonical wording is
[apply-closeout-review spec, Requirement 3](../apply-closeout-review/spec.md).

#### Scenario: Executor closes out a change that produced new findings

- **WHEN** a change's closeout identifies new follow-up candidates
- **THEN** the candidates are surfaced for human discussion before any governance artifact changes
- **AND** the executor does not promote a candidate into a durable rule without that discussion

#### Scenario: Closeout produces no new findings

- **WHEN** a change's closeout identifies no new follow-up work
- **THEN** the closeout states that no new follow-up work was identified
- **AND** no governance artifact changes as a result

### Requirement: Superseded changes are archived rather than deleted

Superseded changes SHALL be archived rather than deleted, so that the decision and the
change it was replaced by remain reconstructable from repository history. Contributors
MUST NOT retire a superseded change by deleting its artifacts or its directory. This
requirement restates the constraint that lives in the durable change-backlog-triage spec
and adds no constraint beyond it; the canonical wording is
[change-backlog-triage spec, Requirement 10](../change-backlog-triage/spec.md).

#### Scenario: A change is replaced before it is implemented

- **WHEN** a maintainer decides a non-archived change has been replaced
- **THEN** the change is retired through an archive operation rather than deletion
- **AND** its artifacts remain reconstructable from repository history

#### Scenario: A superseded change is removed from the active set

- **WHEN** a maintainer removes a superseded change from the active set
- **THEN** the removal does not delete the change's artifacts
- **AND** the operation is not treated as normal directory deletion
