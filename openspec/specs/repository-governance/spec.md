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

### Requirement: Apply-closeout findings require human discussion before promotion

New follow-up candidates discovered during apply closeout SHALL remain explicit review inputs until the human accepts, defers, rejects, or converts them into follow-up work. Agents MUST NOT silently promote apply-closeout findings into queued changes or further implementation without human discussion.

#### Scenario: Apply closeout identifies a workflow-improvement candidate

- **WHEN** an apply closeout reports a new workflow-improvement candidate
- **THEN** the candidate is surfaced as an explicit discussion item
- **AND** the agent waits for human disposition before promoting it into a queued change or further implementation

### Requirement: Discovered work is triaged before scope continues

Work discovered during execution SHALL be classified before implementation continues. Discoveries that are required to complete the current change SHALL update current change artifacts first; prerequisite discoveries SHALL be recorded in a separate change and block the current change when necessary; adjacent discoveries SHALL be captured as follow-up work without silently expanding current scope.

#### Scenario: Executor discovers unfinished prerequisite work

- **WHEN** an executor learns that the current change depends on unfinished prerequisite work
- **THEN** the executor records or continues a separate prerequisite change
- **AND** the current change is marked blocked when the prerequisite prevents correct continuation
- **AND** execution does not proceed on the stale assumption that the prerequisite is already satisfied

### Requirement: Follow-up changes preserve prerequisite evidence context

When a change depends on prior validation, retrospective findings, or archived change conclusions to make its scope understandable, the change SHALL identify the upstream change names and summarize the inherited findings in its proposal or design artifacts. Contributors MUST NOT rely on unstated team memory or metadata-only dependency references as the sole way to reconstruct that context.

#### Scenario: Follow-up optimization change builds on prior validation

- **WHEN** a contributor proposes a follow-up change whose rationale depends on what an earlier validation change already proved
- **THEN** the proposal or design names the upstream validation change
- **AND** the current change summarizes the finding that remains true and the gap that still needs work
- **AND** a fresh reader can understand why the new change exists without separately guessing the evidence chain from oral background alone

#### Scenario: Current change references archived findings

- **WHEN** a non-archived change depends on findings that live in archived change artifacts
- **THEN** the current change cites the archived change by name
- **AND** the current change explains which archived finding is being carried forward into current scope
- **AND** the reader does not need to inspect backlog metadata alone to infer the narrative dependency

### Requirement: Workflow guidance distinguishes artifact readiness from change completion
Repository workflow guidance SHALL distinguish OpenSpec artifact readiness, task completion, and change completion so contributors do not treat a single workflow surface as the complete archive-readiness answer.

#### Scenario: Agent checks whether a change is complete
- **WHEN** a maintainer or agent observes `openspec status --change ...` reporting all artifacts complete
- **THEN** the repository guidance states that this means artifact readiness only
- **AND** the maintainer or agent still checks task progress and closeout expectations before treating the change as complete or archive-ready

### Requirement: Normal OpenSpec operations use workflow tools instead of manual directory manipulation

When an agent or maintainer creates, applies, or archives OpenSpec changes, the repository SHALL direct them to prefer the installed OpenSpec skills first and the official `openspec` commands second. Contributors MUST NOT manually move, recreate, or leave behind `openspec/changes/` directory entries as part of normal workflow unless they are explicitly repairing abnormal repository state.

#### Scenario: Agent starts a new propose or archive operation

- **WHEN** an agent needs to propose, apply, or archive an OpenSpec change
- **THEN** repository guidance points the agent toward the installed OpenSpec skills for that workflow
- **AND** the guidance also allows the official `openspec` CLI as the direct fallback path
- **AND** the agent is not told to treat manual directory manipulation as the normal archive workflow

#### Scenario: Maintainer repairs stale archive residue

- **WHEN** a maintainer finds an archived change that still has a stale active-directory placeholder
- **THEN** the maintainer may remove the stale active placeholder as an explicit repair action
- **AND** the repair does not redefine manual directory edits as the repository's normal archive workflow

### Requirement: Artifact weight follows change type

The repository SHALL define artifact expectations by change type so feature, harness, validation, refactor, and spike work are documented with appropriate weight. Contributors MUST satisfy the repository's minimum artifact policy for the selected change type before implementation is treated as normal workflow.

#### Scenario: Maintainer prepares a validation change

- **WHEN** a maintainer creates a validation-oriented change
- **THEN** the maintainer provides the minimum artifacts required for validation work by repository policy
- **AND** durable product specs are only introduced when the change creates durable validation requirements

### Requirement: Superseded changes are archived rather than deleted
Changes that are no longer the recommended execution path SHALL be marked superseded only as a temporary pre-archive disposition rather than as a normal long-lived planning state. Once their disposition is clear, superseded changes SHALL be archived so they no longer appear in active planning scans, typically without updating main specs when no durable requirement change is being merged.

#### Scenario: Older change is replaced by newer direction
- **WHEN** a maintainer decides that an existing non-archived change has been replaced by a newer change or conclusion
- **THEN** the older change may be marked superseded as a temporary disposition
- **AND** the older change is archived once its disposition is stable
- **AND** the repository keeps the archived record instead of deleting the change from history

#### Scenario: Superseded change lingers in active scans
- **WHEN** a non-archived change remains marked superseded instead of being archived promptly
- **THEN** repository workflow treats that state as archive hygiene debt rather than as a normal steady-state planning bucket
- **AND** maintainers can identify the change as requiring cleanup

### Requirement: Repository-local scratch artifacts stay out of normal working paths

The repository SHALL provide a local-only place for transient validation probes and scratch scripts so ad hoc artifacts do not accumulate in normal source locations. Repository guidance SHALL direct local scratch artifacts into `.tmp/`, and git ignore rules SHALL keep that directory out of normal version control operations.

#### Scenario: Agent needs a temporary validation script

- **WHEN** an agent creates a short-lived probe or scratch script for local validation
- **THEN** the artifact is placed under `.tmp/`
- **AND** that directory does not create normal git tracking noise

