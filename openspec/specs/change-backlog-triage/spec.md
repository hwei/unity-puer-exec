# Change Backlog Triage

## Purpose

Define the repository's machine-readable change metadata, backlog state model, and deterministic next-change tooling for harness-engineering work.
## Requirements
### Requirement: Non-archived changes carry machine-readable backlog metadata

The repository SHALL treat non-archived OpenSpec changes as the canonical planning surface for planned and active work. Each non-archived change SHALL provide a machine-readable `meta.yaml` file that records its current planning state and computable ranking inputs.

#### Scenario: Maintainer creates a queued or active change

- **WHEN** a maintainer or agent creates or updates a non-archived change for repository work
- **THEN** the change includes a repository-owned `meta.yaml` file
- **AND** the metadata records status, change type, priority, blocker references, assumption state, evidence target, and update date

### Requirement: Backlog states are explicit and finite

The repository SHALL represent non-archived change state using the statuses `queued`, `active`, `blocked`, and `superseded`. Contributors MUST NOT rely on implicit prose alone to communicate whether a change should be started or continued.

#### Scenario: Agent inspects candidate work

- **WHEN** an agent or maintainer inspects non-archived changes
- **THEN** each change can be classified from `meta.yaml` as queued, active, blocked, or superseded
- **AND** blocked or superseded work is distinguishable without reading the full change prose

### Requirement: Backlog means queued changes

The repository SHALL define backlog as the subset of non-archived changes whose metadata status is `queued`. Other non-archived statuses MAY appear in planning or ranking views, but they MUST NOT be conflated with backlog.

#### Scenario: Maintainer asks for backlog view

- **WHEN** a maintainer or agent requests the backlog
- **THEN** the returned set contains only changes whose status is `queued`
- **AND** changes in `active`, `blocked`, or `superseded` status are excluded from the backlog view

### Requirement: Dependencies are recorded in one direction

Changes that depend on other changes SHALL record those prerequisites in a `blocked_by` field. The repository MUST NOT require reciprocal dependency fields for backlog ranking or tracing.

#### Scenario: Change depends on unfinished prerequisite

- **WHEN** a change cannot proceed until another change or decision is resolved
- **THEN** the dependent change records the prerequisite in `blocked_by`
- **AND** tooling and agents can identify that the change is not ready to be preferred over unblocked candidates

### Requirement: Change metadata does not replace narrative context

`meta.yaml` SHALL remain machine-readable planning metadata for non-archived changes. Dependency metadata such as `blocked_by` MAY identify prerequisite changes, but it MUST NOT be treated as sufficient by itself to explain the evidence chain, rationale, or inherited findings for follow-up work.

#### Scenario: Maintainer inspects a dependent change

- **WHEN** a maintainer or agent reads `meta.yaml` for a change that depends on earlier work
- **THEN** the metadata exposes machine-readable prerequisite references for tooling
- **AND** repository workflow still expects proposal or design artifacts to explain the human-readable background when that context is necessary
- **AND** the maintainer does not treat dependency metadata alone as the complete explanation of why the change exists

### Requirement: Next-change tooling is deterministic and advisory

The repository SHALL provide a local tool that filters and sorts non-archived changes using only computable metadata and derived dependency counts. The tool SHALL report the reasons for its ordering and SHALL remain advisory rather than directly starting execution.

#### Scenario: Clean working tree requires the next candidate change

- **WHEN** a maintainer or agent needs to identify the best next change from a clean working tree
- **THEN** the tool filters out non-actionable states such as blocked and superseded
- **AND** the remaining candidates are ranked deterministically from metadata fields and derived unlock counts
- **AND** the output explains the ranking inputs for each recommended candidate

### Requirement: Backlog tooling supports metadata filters

The repository SHALL support filtering change views by machine-readable metadata, including at minimum `status` and `change_type`.

#### Scenario: Maintainer filters queued harness work

- **WHEN** a maintainer or agent filters the backlog tooling by `status=queued` and `change_type=harness`
- **THEN** the output contains only queued harness changes
- **AND** the filter does not require ad hoc prose matching

### Requirement: Change-query output distinguishes raw metadata from interpreted state
Repository query tooling SHALL preserve access to a change's raw `meta.yaml` planning state while also surfacing an interpreted operator-facing state when dependency resolution, archived prerequisites, or abnormal repository state make raw metadata alone insufficient for trustworthy planning decisions.

#### Scenario: Query output detects a state interpretation gap
- **WHEN** a maintainer or agent queries a non-archived change whose raw metadata does not cleanly match the effective planning situation
- **THEN** the query surface reports enough information to distinguish raw metadata from the interpreted operator-facing state
- **AND** the output does not silently force contributors to infer which source of truth to trust

### Requirement: Backlog tooling remains a raw metadata surface
Repository backlog tooling SHALL continue to present backlog state from repository-owned `meta.yaml` values rather than silently replacing backlog classification with interpreted OpenSpec workflow state.

#### Scenario: Backlog query sees a queued change that OpenSpec reports as in progress
- **WHEN** a maintainer or agent requests the backlog for a non-archived change whose `meta.yaml` status is `queued`
- **THEN** the backlog surface still treats the change as queued backlog work
- **AND** any interpreted workflow-state comparison is provided by a separate query or diagnostic surface rather than by changing the backlog definition

### Requirement: Change-query output stays trustworthy under inconsistent repository state
Repository query tooling SHALL handle stale placeholders, resolved blockers, or other repository-state inconsistencies in a way that reduces misleading planning output and makes the inconsistency visible for follow-up correction.

#### Scenario: Query output encounters stale or inconsistent change state
- **WHEN** a maintainer or agent queries change state and the repository contains stale or inconsistent planning signals
- **THEN** the query surface remains usable for planning decisions
- **AND** the output makes the inconsistency visible instead of presenting a misleading clean answer

