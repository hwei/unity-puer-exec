## MODIFIED Requirements

### Requirement: Backlog states are explicit and finite
The repository SHALL keep machine-readable change metadata for non-archived changes, but backlog recommendation MUST NOT rely on queued, active, and blocked labels as the primary source of change readiness. Contributors MUST NOT rely on implicit prose alone to communicate whether a change should be started or continued.

#### Scenario: Agent inspects candidate work
- **WHEN** an agent or maintainer inspects non-archived changes
- **THEN** the repository can classify explicit manual disposition such as superseded from machine-readable metadata
- **AND** backlog recommendation is derived from repository facts and diagnostics rather than from queued, active, or blocked labels alone

### Requirement: Backlog means recommendable non-archived changes
The repository SHALL define backlog recommendation as the subset of non-archived changes that are currently eligible based on repository facts such as prerequisite resolution, explicit superseded disposition, and dependency consistency. Metadata values may still be inspected directly, but they MUST NOT be conflated with the repository's derived recommendation set.

#### Scenario: Maintainer asks for backlog view
- **WHEN** a maintainer or agent requests the backlog
- **THEN** the returned set contains only non-archived changes that are currently eligible for recommendation
- **AND** changes excluded by superseded disposition, unresolved prerequisites, or dependency inconsistencies are omitted from the recommendable backlog view

### Requirement: Dependencies are recorded in one direction
Changes that depend on other changes SHALL record those prerequisites in a `blocked_by` field. Repository recommendation tooling MUST treat missing dependency references as inconsistent state rather than silently interpreting them as resolved.

#### Scenario: Change depends on unfinished prerequisite
- **WHEN** a change cannot proceed until another change or decision is resolved
- **THEN** the dependent change records the prerequisite in `blocked_by`
- **AND** tooling can identify that the change is not ready to be preferred over unblocked candidates

#### Scenario: Change references missing prerequisite
- **WHEN** a change records a `blocked_by` dependency that matches neither an active nor archived change
- **THEN** recommendation tooling marks the change as inconsistent
- **AND** the missing dependency is not silently treated as a resolved prerequisite

### Requirement: Next-change tooling is deterministic and advisory
The repository SHALL provide a local tool that filters and sorts non-archived changes using repository facts, computable metadata, and Git-history-derived activity signals. The tool SHALL report the reasons for eligibility, ineligibility, and ordering and SHALL remain advisory rather than directly starting execution.

#### Scenario: Clean working tree requires the next candidate change
- **WHEN** a maintainer or agent needs to identify the best next change from a clean working tree
- **THEN** the tool filters out non-eligible changes such as superseded entries, unresolved dependencies, and inconsistent dependency references
- **AND** the remaining candidates are ranked deterministically from repository facts, metadata fields, derived unlock counts, and Git-history proximity
- **AND** the output explains the ranking inputs and diagnostics for each candidate

## ADDED Requirements

### Requirement: Superseded disposition is temporary and archive-bound
The repository SHALL treat `superseded` as a temporary explicit disposition for non-archived changes that have been replaced, and maintainers SHALL archive superseded changes once their disposition is stable.

#### Scenario: Replaced change awaits archive
- **WHEN** a maintainer decides a non-archived change has been replaced by a newer direction
- **THEN** the change may be marked `superseded`
- **AND** backlog recommendation excludes it while it remains non-archived
- **AND** repository workflow expects it to be archived promptly rather than kept as a normal long-lived planning state

### Requirement: Recommendation ranking may use Git commit distance
Repository backlog recommendation SHALL be allowed to rank eligible changes using Git commit distance from the most recent commit that touched the change directory.

#### Scenario: Recent change is preferred for continuation
- **WHEN** two eligible changes have similar priority and other metadata signals
- **THEN** recommendation tooling may prefer the one touched fewer commits ago
- **AND** that Git-history signal influences ordering without creating a separate active state bucket
