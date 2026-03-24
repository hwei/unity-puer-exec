# Change Backlog Triage

## Purpose

Define the repository's machine-readable change metadata, backlog state model, and deterministic next-change tooling for harness-engineering work.
## Requirements
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

### Requirement: Change metadata does not replace narrative context

`meta.yaml` SHALL remain machine-readable planning metadata for non-archived changes. Dependency metadata such as `blocked_by` MAY identify prerequisite changes, but it MUST NOT be treated as sufficient by itself to explain the evidence chain, rationale, or inherited findings for follow-up work.

#### Scenario: Maintainer inspects a dependent change

- **WHEN** a maintainer or agent reads `meta.yaml` for a change that depends on earlier work
- **THEN** the metadata exposes machine-readable prerequisite references for tooling
- **AND** repository workflow still expects proposal or design artifacts to explain the human-readable background when that context is necessary
- **AND** the maintainer does not treat dependency metadata alone as the complete explanation of why the change exists

### Requirement: Next-change tooling is deterministic and advisory
The repository SHALL provide a local tool that filters and sorts non-archived changes using repository facts, computable metadata, and Git-history-derived activity signals. The tool SHALL report the reasons for eligibility, ineligibility, and ordering and SHALL remain advisory rather than directly starting execution.

#### Scenario: Clean working tree requires the next candidate change
- **WHEN** a maintainer or agent needs to identify the best next change from a clean working tree
- **THEN** the tool filters out non-eligible changes such as superseded entries, unresolved dependencies, and inconsistent dependency references
- **AND** the remaining candidates are ranked deterministically from repository facts, metadata fields, derived unlock counts, and Git-history proximity
- **AND** the output explains the ranking inputs and diagnostics for each candidate

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

### Requirement: Change-query output stays trustworthy under inconsistent repository state
Repository query tooling SHALL handle stale placeholders, resolved blockers, or other repository-state inconsistencies in a way that reduces misleading planning output and makes the inconsistency visible for follow-up correction.

#### Scenario: Query output encounters stale or inconsistent change state
- **WHEN** a maintainer or agent queries change state and the repository contains stale or inconsistent planning signals
- **THEN** the query surface remains usable for planning decisions
- **AND** the output makes the inconsistency visible instead of presenting a misleading clean answer

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

