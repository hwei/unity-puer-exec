## ADDED Requirements

### Requirement: OpenSpec changes are the canonical backlog for non-archived work

The repository SHALL use non-archived OpenSpec changes as the canonical backlog surface for scoped work. Durable specs SHALL describe long-lived repository truth and MUST NOT be used as the sole record of queued implementation work.

#### Scenario: Contributor looks for planned work

- **WHEN** a contributor or agent needs to inspect pending repository work
- **THEN** the contributor reads non-archived changes under `openspec/changes/`
- **AND** durable capability specs are treated as requirements rather than backlog entries

### Requirement: Newly discovered work is triaged before execution continues

Work discovered during execution SHALL be classified before implementation continues. Discoveries that are required to complete the current change SHALL update the current change artifacts first; prerequisite discoveries SHALL be captured in a separate change and block the current change when necessary; adjacent discoveries SHALL be captured as follow-up work without silently expanding current scope.

#### Scenario: Executor finds an unexpected prerequisite

- **WHEN** an executor discovers that the current change depends on unfinished prerequisite work
- **THEN** the executor records or continues a separate prerequisite change
- **AND** the current change is marked blocked when the prerequisite prevents correct continuation
- **AND** execution does not continue on the old assumption as if the prerequisite were already satisfied

### Requirement: Artifact weight follows change type

The repository SHALL define artifact expectations by change type so that feature, harness, validation, refactor, and spike work are documented with appropriate weight. Contributors MUST NOT assume that every change requires the same artifact depth, but they MUST satisfy the repository's minimum artifact policy for the chosen type before implementation is treated as normal workflow.

#### Scenario: Maintainer prepares a validation change

- **WHEN** a maintainer creates a validation-oriented change
- **THEN** the maintainer provides the minimum artifacts required for validation work by repository policy
- **AND** the maintainer does not need to invent durable product specs unless the change creates durable validation requirements

### Requirement: Superseded changes remain historical and leave the backlog

Changes that are no longer the recommended execution path SHALL be marked superseded rather than silently deleted. Once their disposition is clear, superseded changes SHALL be archived so they no longer appear in active backlog scans, typically without updating main specs when no durable requirement change is being merged.

#### Scenario: Planned change is replaced by a newer direction

- **WHEN** a maintainer decides that an existing non-archived change has been replaced by a newer change or conclusion
- **THEN** the older change is marked superseded
- **AND** the older change is archived once its disposition is stable
- **AND** the repository keeps the archived record instead of deleting the change from history
