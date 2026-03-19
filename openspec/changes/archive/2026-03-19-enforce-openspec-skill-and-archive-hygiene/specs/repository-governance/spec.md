## ADDED Requirements

### Requirement: Agents prefer OpenSpec workflow tools over manual change-directory edits
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
