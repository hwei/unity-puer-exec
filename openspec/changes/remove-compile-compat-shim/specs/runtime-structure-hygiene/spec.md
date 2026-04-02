## ADDED Requirements

### Requirement: Temporarily isolated compatibility shims are removed once confirmed dead
If repository-owned runtime cleanup isolates a compatibility shim for later verification, that shim SHALL be removed in a follow-up change once repository inspection confirms it has no remaining repository callers, no authoritative documentation dependency, and no required validation role.

#### Scenario: Previously isolated shim is later confirmed dead
- **WHEN** a follow-up cleanup inspects an isolated compatibility shim and finds no remaining repository callers, no formal spec or README dependency, and no required validation workflow that depends on it
- **THEN** the repository removes the shim instead of preserving it indefinitely as package residue
- **AND** related tests and package-layout assertions stop treating the shim as required structure
