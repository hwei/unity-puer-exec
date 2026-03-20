## ADDED Requirements

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
