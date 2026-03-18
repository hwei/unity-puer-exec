# Runtime Structure Hygiene

## Purpose

Define durable repository expectations for pruning dead transitional runtime code, isolating compatibility shims, and keeping runtime modules aligned to explicit responsibilities.

## Requirements

### Requirement: Confirmed-dead transitional runtime code is removed instead of migrated

Repository-owned runtime code that has no repository callers, no authoritative documentation dependency, and no required validation role SHALL be removed rather than carried into a new structure as historical residue.

#### Scenario: Maintainer confirms a transitional helper is dead

- **WHEN** repository inspection shows that a transitional runtime helper has no remaining repository callers and is not part of a documented formal surface
- **THEN** the change removes that helper instead of relocating it into the refactored structure

### Requirement: Compatibility-only runtime surfaces stay isolated and thin

Compatibility-only runtime entry points or helpers SHALL be implemented as explicit shims. They MUST delegate to the formal runtime behavior and MUST NOT accumulate independent business logic, parallel workflow rules, or separate authoritative documentation.

#### Scenario: Maintainer retains a compatibility entry point

- **WHEN** a compatibility-only entry point is still kept during runtime cleanup
- **THEN** that entry point remains a thin adapter over the formal runtime path
- **AND** the repository does not treat it as an equally authoritative extension surface

### Requirement: Runtime modules align to explicit responsibilities

Repository-owned runtime code SHALL be organized so major responsibilities are split across explicit module boundaries rather than retained in monolithic files that combine unrelated concerns.

#### Scenario: Maintainer reorganizes runtime implementation

- **WHEN** the repository refactors Python or Unity runtime code
- **THEN** session/runtime control, CLI command wiring, help metadata, server lifecycle, job state, and bridge compatibility concerns are assigned to deliberate module boundaries
- **AND** the repository does not preserve monolithic files solely to avoid moving code
