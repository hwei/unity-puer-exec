# Repository Governance

## Purpose

Define the repository's canonical OpenSpec-first workflow, including change gating, durable-truth distillation, and retrospective handling.

## Requirements

### Requirement: OpenSpec is the canonical repository workflow

The repository SHALL use OpenSpec as the canonical system for project context, durable governance rules, and active change planning. Legacy governance documents MUST NOT remain authoritative once their content has been migrated into OpenSpec artifacts, and the working tree SHALL NOT keep a parallel legacy `docs/` workflow entry path.

#### Scenario: Fresh contributor looks for process entry

- **WHEN** a contributor or agent needs the repository workflow entry point
- **THEN** `openspec/project.md` provides repository-wide context
- **AND** `openspec/specs/repository-governance/spec.md` defines the durable workflow rules
- **AND** the working tree does not provide a parallel `docs/` workflow entry path

### Requirement: Substantial work requires OpenSpec change context

Substantial work SHALL be scoped through an OpenSpec change before implementation is treated as canonical. The minimum apply-ready artifact set MUST include proposal, specs, and tasks.

#### Scenario: Repository change is about to begin

- **WHEN** a contributor plans a substantial governance, product, or tooling change
- **THEN** the contributor creates or continues an OpenSpec change
- **AND** implementation does not proceed as normal repository workflow until the change includes proposal, specs, and tasks artifacts

### Requirement: Durable truth is distilled out of temporary execution context

Temporary execution artifacts such as plans, closeout notes, or migration scaffolds SHALL be treated as transient support material. Stable conclusions MUST be distilled into OpenSpec specs, source comments, tests, or other smallest durable destinations before temporary artifacts are discarded.

#### Scenario: Temporary plan completes

- **WHEN** a change-specific plan or execution note is no longer needed for active work
- **THEN** stable conclusions have already been copied into durable OpenSpec or code-local artifacts
- **AND** the temporary artifact is not preserved as the repository's long-lived truth

### Requirement: Retrospectives require explicit disposition

Stable follow-up findings discovered during implementation SHALL remain explicit review inputs until they are accepted, deferred, rejected, or split into follow-up work. Executors MUST NOT silently promote retrospective observations into repository governance rules.

#### Scenario: Implementation reveals a workflow improvement

- **WHEN** an executor identifies a stable workflow finding while closing out a change
- **THEN** the finding is recorded as explicit retrospective context for that change
- **AND** long-lived governance artifacts change only after explicit disposition

### Requirement: Discovered work is triaged before scope continues

Work discovered during execution SHALL be classified before implementation continues. Discoveries that are required to complete the current change SHALL update current change artifacts first; prerequisite discoveries SHALL be recorded in a separate change and block the current change when necessary; adjacent discoveries SHALL be captured as follow-up work without silently expanding current scope.

#### Scenario: Executor discovers unfinished prerequisite work

- **WHEN** an executor learns that the current change depends on unfinished prerequisite work
- **THEN** the executor records or continues a separate prerequisite change
- **AND** the current change is marked blocked when the prerequisite prevents correct continuation
- **AND** execution does not proceed on the stale assumption that the prerequisite is already satisfied

### Requirement: Artifact weight follows change type

The repository SHALL define artifact expectations by change type so feature, harness, validation, refactor, and spike work are documented with appropriate weight. Contributors MUST satisfy the repository's minimum artifact policy for the selected change type before implementation is treated as normal workflow.

#### Scenario: Maintainer prepares a validation change

- **WHEN** a maintainer creates a validation-oriented change
- **THEN** the maintainer provides the minimum artifacts required for validation work by repository policy
- **AND** durable product specs are only introduced when the change creates durable validation requirements

### Requirement: Superseded changes are archived rather than deleted

Changes that are no longer the recommended execution path SHALL be marked superseded rather than silently deleted. Once their disposition is clear, superseded changes SHALL be archived so they no longer appear in active planning scans, typically without updating main specs when no durable requirement change is being merged.

#### Scenario: Older change is replaced by newer direction

- **WHEN** a maintainer decides that an existing non-archived change has been replaced by a newer change or conclusion
- **THEN** the older change is marked superseded
- **AND** the older change is archived once its disposition is stable
- **AND** the repository keeps the archived record instead of deleting the change from history
