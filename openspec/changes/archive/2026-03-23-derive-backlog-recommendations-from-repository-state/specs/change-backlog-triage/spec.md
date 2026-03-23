## ADDED Requirements

### Requirement: Backlog recommendation may derive eligibility from repository facts
Repository backlog recommendation SHALL be allowed to derive whether a non-archived change is currently eligible for recommendation from repository facts such as prerequisite resolution, archive state, and repository consistency checks rather than relying only on manually maintained planning status transitions.

#### Scenario: Change has only resolved prerequisites
- **WHEN** a maintainer or agent evaluates a non-archived change whose recorded prerequisites are all resolved by existing or archived repository state
- **THEN** the backlog model may treat the change as eligible for recommendation even if no separate manual "ready" transition was recorded

#### Scenario: Recommendation no longer depends on queued or active labels
- **WHEN** a maintainer or agent evaluates a non-archived change under the derived backlog model
- **THEN** recommendation eligibility does not require a separate queued or active status label
- **AND** the surface can explain eligibility from repository facts instead

### Requirement: Missing dependency references are surfaced as diagnostics
When a change references a prerequisite through `blocked_by` and no matching active or archived change can be found, repository backlog tooling SHALL surface that inconsistency as a diagnostic instead of silently treating the dependency as resolved.

#### Scenario: Change references a missing prerequisite
- **WHEN** a maintainer or agent evaluates a change whose `blocked_by` entry does not match any non-archived or archived change
- **THEN** the backlog surface reports the dependency as inconsistent
- **AND** the missing reference is not silently counted as a resolved prerequisite

### Requirement: Superseded disposition remains explicit until archive
Changes that are no longer the recommended execution path SHALL remain explicitly distinguishable from recommendable backlog candidates until they are archived, even if other backlog recommendation signals become more derived.

#### Scenario: Replaced change remains non-archived before archive
- **WHEN** a maintainer decides a non-archived change has been replaced by a newer direction
- **THEN** the repository keeps an explicit superseded-style disposition for that change
- **AND** backlog recommendation does not treat it as a normal candidate while it awaits archive
- **AND** the disposition is treated as temporary rather than as a normal long-lived planning bucket

### Requirement: Recent activity ranking may use Git commit distance
Repository backlog recommendation SHALL be allowed to rank otherwise eligible changes using Git-history proximity such as commit distance from the most recent commit touching the change directory, rather than relying only on wall-clock timestamps.

#### Scenario: Two eligible changes differ in Git-history proximity
- **WHEN** a maintainer or agent compares two eligible non-archived changes with similar metadata priority
- **THEN** the backlog model may prefer the change whose directory was touched fewer commits ago
- **AND** that activity signal influences ranking rather than silently rewriting archived or superseded disposition

### Requirement: Backlog recommendation separates eligibility from ordering
Repository backlog tooling SHALL be able to distinguish whether a change is eligible for recommendation from how strongly it should be preferred among other eligible changes.

#### Scenario: Eligible changes are ranked without changing disposition
- **WHEN** a maintainer or agent compares multiple eligible changes
- **THEN** the tooling can rank them using recommendation signals such as priority and Git-history proximity
- **AND** those ordering signals do not silently create long-lived planning states such as active or blocked
