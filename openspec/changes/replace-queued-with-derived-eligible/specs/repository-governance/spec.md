## MODIFIED Requirements

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

### Requirement: Workflow guidance distinguishes artifact readiness from change completion
Repository workflow guidance SHALL distinguish OpenSpec artifact readiness, task completion, and change completion so contributors do not treat a single workflow surface as the complete archive-readiness answer.

#### Scenario: Agent checks whether a change is complete
- **WHEN** a maintainer or agent observes `openspec status --change ...` reporting all artifacts complete
- **THEN** the repository guidance states that this means artifact readiness only
- **AND** the maintainer or agent still checks task progress and closeout expectations before treating the change as complete or archive-ready
