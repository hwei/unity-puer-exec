## MODIFIED Requirements

### Requirement: OpenSpec is the canonical repository workflow

The repository SHALL use OpenSpec as the canonical system for project context, durable governance rules, and active change planning. Legacy governance documents MUST NOT remain authoritative once their content has been migrated into OpenSpec artifacts, and legacy workflow docs do not remain in the working tree as a parallel entry path.

#### Scenario: Fresh contributor looks for process entry

- **WHEN** a contributor or agent needs the repository workflow entry point
- **THEN** `openspec/project.md` provides repository-wide context
- **AND** `openspec/specs/repository-governance/spec.md` defines the durable workflow rules
- **AND** the working tree does not provide a parallel `docs/` workflow entry path

