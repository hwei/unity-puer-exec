## ADDED Requirements

### Requirement: OpenSpec is the canonical governance entry point

The repository SHALL use OpenSpec artifacts as the canonical source of truth for project context, durable governance rules, and active change planning. Legacy `docs/` workflow files MUST NOT remain authoritative once equivalent OpenSpec artifacts exist.

#### Scenario: Fresh agent session loads repository context

- **WHEN** an agent or contributor needs the repository governance entry point
- **THEN** the repository provides project-wide context through `openspec/project.md`
- **AND** durable workflow requirements are defined in `openspec/specs/repository-governance/spec.md`
- **AND** legacy `docs/` files act only as redirects or historical references

### Requirement: Substantial work is gated by an OpenSpec change

Substantial repository changes SHALL be captured as OpenSpec changes before implementation begins. The change MUST define proposal, specs, and implementation tasks before apply work is treated as ready.

#### Scenario: Contributor starts substantial repository work

- **WHEN** a planned change affects repository behavior, product behavior, or governance behavior materially
- **THEN** the contributor creates or continues an OpenSpec change under `openspec/changes/`
- **AND** implementation does not proceed as canonical workflow until the change has proposal, specs, and tasks artifacts

### Requirement: Temporary execution context is ephemeral

Temporary execution context such as plans, working notes, or migration scaffolds SHALL be treated as transient implementation support. Durable conclusions MUST be distilled into `openspec/project.md`, `openspec/specs/`, tests, or source comments before the transient artifact is removed.

#### Scenario: Change-specific planning work completes

- **WHEN** a temporary plan or execution note has served its implementation purpose
- **THEN** stable conclusions are moved into the smallest durable OpenSpec or code-local destination that matches their scope
- **AND** the temporary artifact is not retained as the long-lived source of truth

### Requirement: Retrospectives require explicit disposition

Stable follow-up findings discovered during implementation SHALL remain explicit discussion inputs until they are accepted, deferred, rejected, or split into follow-up work. An agent MUST NOT silently rewrite long-lived governance rules based only on retrospective observations.

#### Scenario: Implementation reveals a workflow improvement idea

- **WHEN** an executor finds a stable governance follow-up while finishing a change
- **THEN** the finding is recorded as a retrospective note in the active change context
- **AND** the finding is not treated as accepted governance until explicitly dispositioned

