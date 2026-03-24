## MODIFIED Requirements

### Requirement: Non-archived changes carry machine-readable backlog metadata

The repository SHALL treat non-archived OpenSpec changes as the canonical planning surface for planned and active work. Each non-archived change SHALL provide a machine-readable `meta.yaml` file that records its current ranking inputs, prerequisite references, and any explicit exception disposition that cannot be derived from repository facts alone.

#### Scenario: Maintainer creates a non-archived change

- **WHEN** a maintainer or agent creates or updates a non-archived change for repository work
- **THEN** the change includes a repository-owned `meta.yaml` file
- **AND** the metadata records change type, priority, blocker references, assumption state, evidence target, update date, and any explicit exception disposition that applies

### Requirement: Backlog states are explicit and finite
The repository SHALL keep machine-readable change metadata for non-archived changes, but backlog recommendation MUST NOT rely on manual queued or active labels as the primary source of readiness. Contributors MUST NOT rely on implicit prose alone to communicate whether a change should be started or continued.

#### Scenario: Agent inspects candidate work
- **WHEN** an agent or maintainer inspects non-archived changes
- **THEN** the repository can classify explicit manual disposition such as blocked or superseded from machine-readable metadata
- **AND** backlog recommendation is derived from repository facts and diagnostics rather than from manual queued or active labels

### Requirement: Backlog means eligible changes
The repository SHALL define backlog recommendation as the subset of non-archived changes that are currently `eligible` based on repository facts such as unfinished tasks, prerequisite resolution, explicit exception disposition, and dependency consistency. Metadata values may still be inspected directly, but they MUST NOT be conflated with the repository's derived recommendation set.

#### Scenario: Maintainer asks for backlog view
- **WHEN** a maintainer or agent requests the backlog
- **THEN** the returned set contains only non-archived changes that are currently eligible for recommendation
- **AND** changes excluded by explicit blocked or superseded disposition, unresolved prerequisites, missing tasks, or dependency inconsistencies are omitted from the recommendable backlog view

### Requirement: Backlog tooling supports metadata filters
The repository SHALL support filtering change views by both derived recommendation status and raw metadata where each is useful for inspection.

#### Scenario: Maintainer filters recommendable harness work
- **WHEN** a maintainer or agent filters backlog tooling by derived `status=eligible` and `change_type=harness`
- **THEN** the output contains only recommendable harness changes
- **AND** the filter does not require ad hoc prose matching

#### Scenario: Maintainer inspects raw superseded metadata
- **WHEN** a maintainer or agent needs raw metadata inspection rather than recommendable backlog filtering
- **THEN** the tooling allows an explicit raw metadata filter such as `meta_status=superseded`
- **AND** the raw inspection path remains distinguishable from the derived recommendation path

### Requirement: Change-query output distinguishes raw metadata from interpreted state
Repository query tooling SHALL preserve access to a change's raw `meta.yaml` planning metadata while also surfacing interpreted operator-facing state when dependency resolution, task progress, archived prerequisites, generic OpenSpec workflow reporting, or abnormal repository state make raw metadata alone insufficient for trustworthy planning decisions.

#### Scenario: Query output detects a state interpretation gap
- **WHEN** a maintainer or agent queries a non-archived change whose raw metadata does not cleanly match the effective planning situation
- **THEN** the query surface reports enough information to distinguish raw metadata from the interpreted operator-facing state
- **AND** the output does not silently force contributors to infer which source of truth to trust

#### Scenario: Derived backlog state replaces raw queued metadata
- **WHEN** a non-archived change has unfinished tasks, no unresolved prerequisites, and no explicit blocked or superseded disposition
- **THEN** repository recommendation tooling may report the change as derived `eligible`
- **AND** the query surface does not require raw `meta.yaml.status = queued` in order to recommend the change
