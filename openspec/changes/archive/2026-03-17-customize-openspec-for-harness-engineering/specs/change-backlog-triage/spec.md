## ADDED Requirements

### Requirement: Non-archived changes carry machine-readable backlog metadata

The repository SHALL treat non-archived OpenSpec changes as the canonical backlog surface for planned and active work. Each non-archived change SHALL provide a machine-readable metadata file that records its current planning state and computable ranking inputs.

#### Scenario: Maintainer creates a queued or active change

- **WHEN** a maintainer or agent creates or updates a non-archived change for repository work
- **THEN** the change includes a repository-owned metadata file
- **AND** the metadata records status, change type, priority, blocker references, assumption state, evidence target, and update date

### Requirement: Change backlog states are explicit and finite

The repository SHALL represent non-archived change state using the statuses `queued`, `active`, `blocked`, and `superseded`. Contributors MUST NOT rely on implicit prose alone to communicate whether a change should be started or continued.

#### Scenario: Agent inspects candidate work

- **WHEN** an agent or maintainer inspects non-archived changes
- **THEN** each change can be classified from its metadata as queued, active, blocked, or superseded
- **AND** blocked or superseded work is distinguishable without reading the full change prose

### Requirement: Backlog means queued changes

The repository SHALL define backlog as the subset of non-archived changes whose metadata status is `queued`. Other non-archived statuses MAY appear in planning or ranking views, but they MUST NOT be conflated with backlog.

#### Scenario: Maintainer asks for backlog view

- **WHEN** a maintainer or agent requests the backlog
- **THEN** the returned set contains changes whose status is `queued`
- **AND** changes in `active`, `blocked`, or `superseded` status are excluded from the backlog view

### Requirement: Dependencies are recorded in one direction

Changes that depend on other changes SHALL record those prerequisites in a `blocked_by` field. The repository MUST NOT require reciprocal dependency fields for backlog ranking or tracing.

#### Scenario: Change depends on unfinished prerequisite

- **WHEN** a change cannot proceed until another change or decision is resolved
- **THEN** the dependent change records the prerequisite in `blocked_by`
- **AND** tooling and agents can identify that the change is not ready to be preferred over unblocked candidates

### Requirement: Next-change ranking is deterministic and advisory

The repository SHALL provide a local tool that filters and sorts non-archived changes using only computable metadata and derived dependency counts. The tool SHALL report the reasons for its ordering and SHALL remain advisory rather than directly starting execution.

#### Scenario: Clean working tree requires the next candidate change

- **WHEN** a maintainer or agent needs to identify the best next change from a clean working tree
- **THEN** the tool filters out non-actionable states such as blocked and superseded
- **AND** the remaining candidates are ranked deterministically from metadata fields and derived unlock counts
- **AND** the output explains the ranking inputs for each recommended candidate
